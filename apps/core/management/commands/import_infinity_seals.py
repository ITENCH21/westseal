"""
Import seal profile cards from https://infinity-seals.ru/

Sections imported:
  /piston-seals/   → uplotnenija_porshnja
  /rod-seals/      → uplotnenija_shtoka
  /wipers/         → grjazesemniki
  /guide-rings/    → napravljajuwie_gidrocilindrov

Usage:
    python manage.py import_infinity_seals
    python manage.py import_infinity_seals --section piston-seals --limit 5
    python manage.py import_infinity_seals --no-images --sleep 0.5
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

BASE_URL = "https://infinity-seals.ru"
SLUG_PREFIX = "infinity-"

SECTIONS = [
    ("piston-seals",  "piston-seals",  "uplotnenija_porshnja"),
    ("rod-seals",     "rod-seals",     "uplotnenija_shtoka"),
    ("wipers",        "wipers",        "grjazesemniki"),
    ("guide-rings",   "guide-rings",   "napravljajuwie_gidrocilindrov"),
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


def _full_url(href: str) -> str:
    return urllib.parse.urljoin(BASE_URL, href) if href else ""


class Command(BaseCommand):
    help = "Import seal profile cards from infinity-seals.ru"

    def add_arguments(self, parser):
        parser.add_argument("--section", help="Only import one section slug (e.g. piston-seals)")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--no-images", action="store_true")
        parser.add_argument("--sleep", type=float, default=0.7)
        parser.add_argument("--log-file", default="data/import_infinity.log")

    def handle(self, *args, **options):
        log_fp = open(options["log_file"], "a", encoding="utf-8")

        def log(msg):
            self.stdout.write(msg)
            log_fp.write(msg + "\n")
            log_fp.flush()

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; WESTSEAL bot/2.0)",
            "Accept-Language": "ru,en;q=0.8",
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
        start_ts = time.time()

        for slug_key, url_path, db_slug in sections:
            cat = SealCategory.objects.filter(slug=db_slug, is_active=True).first()
            if not cat:
                log(f"WARNING: category not found: {db_slug!r} — skipping")
                continue

            section_url = f"{BASE_URL}/{url_path}/"
            log(f"\nSection: {slug_key} → {cat.name}")
            log(f"  URL: {section_url}")

            try:
                html = session.get(section_url, timeout=30).text
            except Exception as exc:
                log(f"  ERROR: {exc}")
                continue

            soup = BeautifulSoup(html, "html.parser")
            product_links = self._extract_links(soup, url_path)
            log(f"  Found {len(product_links)} product links")

            for idx, url in enumerate(product_links, 1):
                if options["limit"] and total_imported >= options["limit"]:
                    break
                try:
                    product = self._parse_product(session, url, cat, options["no_images"])
                except Exception as exc:
                    log(f"  FAIL [{idx}] {url}: {exc}")
                    continue

                total_imported += 1
                elapsed = max(0.1, time.time() - start_ts)
                eta = int((len(product_links) - idx) / (total_imported / elapsed) / 60)
                log(f"  [{idx}/{len(product_links)}] {product.name}  (total={total_imported}, eta~{eta}m)")
                time.sleep(options["sleep"])

        log(f"\nDone. Imported {total_imported} products from infinity-seals.ru")
        log_fp.close()

    def _extract_links(self, soup: BeautifulSoup, url_path: str) -> list[str]:
        prefix = f"/{url_path}/"
        seen, result = set(), []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            path = urllib.parse.urlparse(href).path
            if not path.startswith(prefix):
                continue
            tail = path[len(prefix):].strip("/")
            if not tail or "/" in tail:
                continue
            if path in seen:
                continue
            seen.add(path)
            result.append(_full_url(path))
        return result

    def _parse_product(
        self, session: requests.Session, url: str, cat: SealCategory, skip_images: bool
    ) -> SealProduct:
        html = session.get(url, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")

        # Title
        h1 = soup.find("h1")
        title = _norm(h1.get_text(" ", strip=True)) if h1 else ""
        if not title:
            og = soup.find("meta", property="og:title")
            title = _norm(og.get("content", "")) if og else ""
        if not title:
            raise ValueError("no title")

        # Description: paragraphs in main content area
        main = soup.find("main") or soup.find("article") or soup
        desc_parts = []
        for p in main.find_all("p"):
            t = _norm(p.get_text(" ", strip=True))
            if len(t) > 40:
                desc_parts.append(t)
        description = "\n".join(desc_parts)

        # Attributes: all tables on page
        attributes: list[dict] = []
        attrs_text_parts: list[str] = []

        for table in main.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue
            # Try to detect if this is a characteristics table
            headers = [_norm(c.get_text(" ", strip=True)) for c in rows[0].find_all(["th", "td"])]
            if len(headers) < 2:
                continue

            # Key-value style table (2 columns: name / value)
            if len(headers) == 2 and headers[0] and headers[1]:
                for row in rows:
                    cells = row.find_all(["th", "td"])
                    if len(cells) == 2:
                        k = _norm(cells[0].get_text(" ", strip=True))
                        v = _norm(cells[1].get_text(" ", strip=True))
                        if k and v and k != v:
                            attributes.append({"name": k, "value": v})
                            attrs_text_parts.append(f"{k}: {v}")
                continue

            # Multi-column characteristics table (material, temp, pressure, speed)
            material_col_idx = next(
                (i for i, h in enumerate(headers) if re.search(r"материал|material", h, re.I)), None
            )
            for row in rows[1:]:
                cells = row.find_all(["th", "td"])
                row_vals = [_norm(c.get_text(" ", strip=True)) for c in cells]
                parts = []
                for j, h in enumerate(headers):
                    if j < len(row_vals) and row_vals[j] and row_vals[j] != "-":
                        parts.append(f"{h}: {row_vals[j]}")
                if parts:
                    material = row_vals[material_col_idx] if material_col_idx is not None and material_col_idx < len(row_vals) else ""
                    name = f"Характеристики ({material})" if material else "Характеристики"
                    val = " | ".join(parts)
                    attributes.append({"name": name, "value": val})
                    attrs_text_parts.append(val)

        # Image
        image_url = ""
        og_img = soup.find("meta", property="og:image")
        if og_img:
            image_url = og_img.get("content", "")
        if not image_url:
            img = main.find("img", src=lambda s: s and "wp-content/uploads" in s)
            if img:
                image_url = _full_url(img.get("src", ""))

        # Save
        obj = SealProduct.objects.filter(source_url=url).first()
        if not obj:
            obj = SealProduct(source_url=url, slug=_unique_slug(title))

        obj.name = title
        obj.name_en = title  # already somewhat describes in Russian
        obj.category = cat
        obj.subcategory = None
        obj.image_url = image_url
        obj.description = description
        obj.attributes = attributes
        obj.attributes_text = " | ".join(attrs_text_parts)
        obj.is_active = True

        if image_url and not skip_images:
            try:
                r = session.get(image_url, timeout=30)
                if r.ok:
                    fname = image_url.split("/")[-1].split("?")[0] or "img.jpg"
                    obj.image.save(fname, ContentFile(r.content), save=False)
            except Exception:
                pass

        obj.save()
        return obj
