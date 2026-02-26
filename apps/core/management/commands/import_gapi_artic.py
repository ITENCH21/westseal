"""
Import seal profile cards from https://www.gapi.co.uk/Products/

Sections imported:
  /Products/Piston_Seals  → uplotnenija_porshnja
  /Products/Rod_Seals     → uplotnenija_shtoka
  /Products/Wipers        → grjazesemniki
  /Products/Wear_Rings    → napravljajuwie_gidrocilindrov
  /Products/Static_Seals  → kolca_uplatnitelnye

Profiles are listed in <table> rows on each category page.
Columns vary per page but typically:
  Profile | Profile image | Temp | Pressure | Speed | Material | Application

source_url = page_url + "#" + profile_code

Usage:
    python manage.py import_gapi_artic
    python manage.py import_gapi_artic --section Piston_Seals
    python manage.py import_gapi_artic --no-images
"""
import re
import time
import urllib.parse
from html import unescape

import requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.core.models import SealCategory, SealProduct

BASE_URL = "https://www.gapi.co.uk"
SLUG_PREFIX = "gapi-"

SECTIONS = [
    ("Piston_Seals",  "/Products/Piston_Seals",  "uplotnenija_porshnja"),
    ("Rod_Seals",     "/Products/Rod_Seals",      "uplotnenija_shtoka"),
    ("Wipers",        "/Products/Wipers",         "grjazesemniki"),
    ("Wear_Rings",    "/Products/Wear_Rings",      "napravljajuwie_gidrocilindrov"),
    ("Static_Seals",  "/Products/Static_Seals",   "kolca_uplatnitelnye"),
]


def _norm(text: str) -> str:
    if not text:
        return ""
    text = unescape(text).replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text


def _unique_slug(base: str) -> str:
    slug = SLUG_PREFIX + (slugify(base) or "item")
    idx = 2
    while SealProduct.objects.filter(slug=slug).exists():
        slug = SLUG_PREFIX + (slugify(base) or "item") + f"-{idx}"
        idx += 1
    return slug



class Command(BaseCommand):
    help = "Import seal profile cards from gapi.co.uk (table-based profiles)"

    def add_arguments(self, parser):
        parser.add_argument("--section", help="Only import one section (e.g. Piston_Seals)")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--no-images", action="store_true")
        parser.add_argument("--sleep", type=float, default=0.3)
        parser.add_argument("--log-file", default="data/import_gapi.log")

    def handle(self, *args, **options):
        log_fp = open(options["log_file"], "a", encoding="utf-8")

        def log(msg):
            self.stdout.write(msg)
            log_fp.write(msg + "\n")
            log_fp.flush()

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; WESTSEAL bot/2.0)",
            "Accept-Language": "en,ru;q=0.8",
        })

        sections = SECTIONS
        if options["section"]:
            sections = [s for s in SECTIONS if s[0] == options["section"]]
            if not sections:
                self.stdout.write(self.style.WARNING(
                    f"Unknown section. Available: {', '.join(s[0] for s in SECTIONS)}"
                ))
                return

        total_imported = 0

        for slug_key, url_path, db_slug in sections:
            cat = SealCategory.objects.filter(slug=db_slug, is_active=True).first()
            if not cat:
                log(f"WARNING: category not found: {db_slug!r} — skipping")
                continue

            page_url = BASE_URL + url_path
            log(f"\nSection: {slug_key} → {cat.name}")
            log(f"  URL: {page_url}")

            try:
                html = session.get(page_url, timeout=30).text
            except Exception as exc:
                log(f"  ERROR fetching: {exc}")
                continue

            soup = BeautifulSoup(html, "html.parser")
            page_desc = self._page_description(soup)
            profiles = self._extract_table_profiles(soup, page_url)
            log(f"  Found {len(profiles)} profiles")

            for idx, profile in enumerate(profiles, 1):
                if options["limit"] and total_imported >= options["limit"]:
                    break
                # Prepend page description to each profile description if present
                if page_desc and not profile.get("description"):
                    profile["description"] = page_desc
                try:
                    product = self._save_profile(session, profile, cat, options["no_images"])
                except Exception as exc:
                    log(f"  FAIL [{idx}] {profile.get('code','?')}: {exc}")
                    continue

                total_imported += 1
                log(f"  [{idx}/{len(profiles)}] {product.name}  (total={total_imported})")
                if options["sleep"]:
                    time.sleep(options["sleep"])

        log(f"\nDone. Imported {total_imported} products from gapi.co.uk")
        log_fp.close()

    # ------------------------------------------------------------------ #

    def _page_description(self, soup: BeautifulSoup) -> str:
        """Extract introductory description paragraphs from the page."""
        parts = []
        for p in soup.find_all("p"):
            t = _norm(p.get_text(" ", strip=True))
            if len(t) > 60:
                parts.append(t)
        return "\n".join(parts[:3])  # at most 3 paragraphs

    def _extract_table_profiles(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        """
        GAPI page structure: table rows with no text headers.
        Each data row has 7 columns:
          0: profile code  (or image thumb)
          1: profile code (same, or anchor)
          2: temperature
          3: pressure
          4: speed
          5: material
          6: application

        We detect data rows by checking that the first non-empty cell looks like
        a profile code (2-10 uppercase chars, may contain + / digits).
        """
        profiles = []
        seen: set[str] = set()

        # Fixed column mapping (0-based) — applies when row has ≥ 5 cells
        FIXED_COLS = {
            2: "Temperature",
            3: "Pressure",
            4: "Speed",
            5: "Material",
            6: "Application",
        }

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["th", "td"])
                if len(cells) < 5:
                    continue

                row_vals = [_norm(c.get_text(" ", strip=True)) for c in cells]

                # Determine code: first cell that looks like a profile designation
                code = ""
                img_col_offset = 0
                for ci, val in enumerate(row_vals[:3]):
                    if re.match(r"^[A-Z][A-Z0-9+/\-]{1,9}$", val):
                        code = val
                        # If code is in col 1, col 0 is the image
                        if ci == 1:
                            img_col_offset = 1
                        break

                if not code or code in seen:
                    continue

                seen.add(code)

                # Extract image from first cell (col 0)
                image_url = ""
                img_tag = cells[0].find("img", src=True)
                if img_tag:
                    src = img_tag.get("src", "")
                    image_url = src if src.startswith("http") else urllib.parse.urljoin(BASE_URL, src)

                # Build attributes using fixed column positions, shifted by img_col_offset
                attributes = []
                attrs_text_parts = []
                for base_col, attr_name in FIXED_COLS.items():
                    actual_col = base_col + img_col_offset
                    if actual_col < len(row_vals):
                        v = row_vals[actual_col]
                        if v and v not in ("-", ""):
                            attributes.append({"name": attr_name, "value": v})
                            attrs_text_parts.append(f"{attr_name}: {v}")

                profiles.append({
                    "code": code,
                    "source_url": page_url.split("?")[0].rstrip("/") + "#" + code,
                    "image_url": image_url,
                    "description": "",
                    "attributes": attributes,
                    "attrs_text": " | ".join(attrs_text_parts),
                })

        return profiles

    def _save_profile(
        self, session: requests.Session, profile: dict, cat: SealCategory, skip_images: bool
    ) -> SealProduct:
        url = profile["source_url"]
        obj = SealProduct.objects.filter(source_url=url).first()
        if not obj:
            name = f"GAPI seal {profile['code']}"
            obj = SealProduct(source_url=url, slug=_unique_slug(name))
        else:
            name = obj.name

        name = f"GAPI seal {profile['code']}"

        obj.name = name
        obj.name_en = name
        obj.category = cat
        obj.subcategory = None
        obj.image_url = profile["image_url"]
        obj.description = profile["description"]
        obj.attributes = profile["attributes"]
        obj.attributes_text = profile["attrs_text"]
        obj.is_active = True

        if profile["image_url"] and not skip_images:
            try:
                r = session.get(profile["image_url"], timeout=20)
                if r.ok:
                    fname = profile["image_url"].split("/")[-1].split("?")[0] or "profile.png"
                    obj.image.save(fname, ContentFile(r.content), save=False)
            except Exception:
                pass

        obj.save()
        return obj
