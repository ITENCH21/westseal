"""
Import seal profile cards from https://seal-tech.ru/

Each card represents a profile type (e.g. PS01, WR01) — no size-specific data.
Imports: name, description, characteristics table, image.

Category mapping (seal-tech → our DB slug):
  porshnevye-uplotneniya          → uplotnenija_porshnja
  gryazesemniki                   → grjazesemniki
  shtokovye-uplotneniya           → uplotnenija_shtoka
  simmetrichnye-uplotneniya       → krpms-simmetrichnye-uplotneniya
  opornye-kolca                   → krpms-opornye-koltsa
  napravlyayushhie-kolca          → napravljajuwie_gidrocilindrov
  rotornye-uplotneniya            → krpms-rotornye-uplotneniya
  kolcevye-uplotneniya            → kolca_uplatnitelnye
  importnye • gryazesemniki       → grjazesemniki
  importnye • shtokovye-32        → uplotnenija_shtoka
  importnye • porshnevye-33       → uplotnenija_porshnja
  importnye • lenta-napravlyayushhaya → napravljajuwie_gidrocilindrov

Usage:
    python manage.py import_sealtech
    python manage.py import_sealtech --limit 5 --no-images
    python manage.py import_sealtech --category gryazesemniki
    python manage.py import_sealtech --sleep 0.5 --log-file data/import_sealtech.log
"""
import re
import time
import urllib.parse
from html import unescape
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.core.models import SealCategory, SealProduct

BASE_URL = "https://seal-tech.ru"
SLUG_PREFIX = "sealtech-"

# ---------------------------------------------------------------------------
# Category map: seal-tech URL path segment → our canonical category slug
# Updated to use the merged category slugs.
# ---------------------------------------------------------------------------
CATALOG_SECTIONS = [
    # (section_path, subcategory_slug_in_url, our_category_slug)
    ("/katalog/proizvodstvo-uplotnenijj/porshnevye-uplotneniya/",    "porshnevye-uplotneniya",    "uplotnenija_porshnja"),
    ("/katalog/proizvodstvo-uplotnenijj/gryazesemniki/",             "gryazesemniki",             "grjazesemniki"),
    ("/katalog/proizvodstvo-uplotnenijj/shtokovye-uplotneniya/",     "shtokovye-uplotneniya",     "uplotnenija_shtoka"),
    ("/katalog/proizvodstvo-uplotnenijj/simmetrichnye-uplotneniya/", "simmetrichnye-uplotneniya", "krpms-simmetrichnye-uplotneniya"),
    ("/katalog/proizvodstvo-uplotnenijj/opornye-kolca/",             "opornye-kolca",             "krpms-opornye-koltsa"),
    ("/katalog/proizvodstvo-uplotnenijj/napravlyayushhie-kolca/",    "napravlyayushhie-kolca",    "napravljajuwie_gidrocilindrov"),
    ("/katalog/proizvodstvo-uplotnenijj/rotornye-uplotneniya/",      "rotornye-uplotneniya",      "krpms-rotornye-uplotneniya"),
    ("/katalog/proizvodstvo-uplotnenijj/kolcevye-uplotneniya/",      "kolcevye-uplotneniya",      "kolca_uplatnitelnye"),
    ("/katalog/importnye-uplotneniya/gryazesemniki/",                "importnye-gryazesemniki",   "grjazesemniki"),
    ("/katalog/importnye-uplotneniya/shtokovye-uplotneniya-32/",     "importnye-shtokovye",       "uplotnenija_shtoka"),
    ("/katalog/importnye-uplotneniya/porshnevye-uplotneniya-33/",    "importnye-porshnevye",      "uplotnenija_porshnja"),
    ("/katalog/importnye-uplotneniya/lenta-napravlyayushhaya/",      "lenta-napravlyayushhaya",   "napravljajuwie_gidrocilindrov"),
]


def _full_url(href: str) -> str:
    return urllib.parse.urljoin(BASE_URL, href) if href else ""


def _norm_path(href: str) -> str:
    path = urllib.parse.urlparse(href.split("#")[0]).path or href
    # Ensure leading slash (page hrefs may be relative without leading /)
    if path and not path.startswith("/"):
        path = "/" + path
    return path


def _normalize_text(value: str, *, keep_newlines: bool = False) -> str:
    if not value:
        return ""
    text = unescape(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    if keep_newlines:
        text = "\n".join(re.sub(r"[ \t\f\v]+", " ", ln).strip() for ln in text.split("\n"))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text
    text = text.replace("\n", " ")
    text = re.sub(r"[ \t\f\v]+", " ", text).strip()
    return text


def _unique_slug(model, base: str) -> str:
    base_slug = slugify(base) or "item"
    slug = base_slug
    idx = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{idx}"
        idx += 1
    return slug


def _is_product_url(path: str, section_path: str) -> bool:
    """Product URL has one extra segment compared to section_path."""
    if not path.startswith(section_path):
        return False
    relative = path[len(section_path):].strip("/")
    # Only one segment remaining (the product slug) with no further nesting
    return "/" not in relative and bool(relative)


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Import seal profile cards from seal-tech.ru into local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            help="Parse only one category by its seal-tech slug (e.g. gryazesemniki)",
        )
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Limit total products to import (0 = no limit)",
        )
        parser.add_argument(
            "--no-images", action="store_true",
            help="Skip downloading images",
        )
        parser.add_argument(
            "--sleep", type=float, default=0.5,
            help="Delay between requests (seconds)",
        )
        parser.add_argument(
            "--log-file", default="data/import_sealtech.log",
            help="Log file path",
        )

    def handle(self, *args, **options):
        log_fp = open(options["log_file"], "a", encoding="utf-8")

        def log(msg: str):
            self.stdout.write(msg)
            log_fp.write(msg + "\n")
            log_fp.flush()

        start_ts = time.time()
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; WESTSEAL bot/2.0)",
            "Accept-Language": "ru,en;q=0.8",
        })

        sections = CATALOG_SECTIONS
        if options["category"]:
            sections = [s for s in CATALOG_SECTIONS if s[1] == options["category"]
                        or options["category"] in s[0]]
            if not sections:
                self.stdout.write(self.style.WARNING(
                    "Category not found. Available: " +
                    ", ".join(s[1] for s in CATALOG_SECTIONS)
                ))
                return

        # Pre-load category objects
        cat_cache: dict[str, SealCategory] = {}
        for _path, _slug_key, db_slug in sections:
            if db_slug not in cat_cache:
                cat = SealCategory.objects.filter(slug=db_slug, is_active=True).first()
                if not cat:
                    log(f"  WARNING: DB category not found: {db_slug!r} — skipping section")
                    cat_cache[db_slug] = None
                else:
                    cat_cache[db_slug] = cat

        total_imported = 0

        for section_path, slug_key, db_slug in sections:
            if options["limit"] and total_imported >= options["limit"]:
                break
            cat_obj = cat_cache.get(db_slug)
            if cat_obj is None:
                continue

            section_url = BASE_URL + section_path
            log(f"\nSection: {slug_key}  →  category: {cat_obj.name} [{db_slug}]")
            log(f"  URL: {section_url}")

            try:
                html = session.get(section_url, timeout=30).text
            except Exception as exc:
                log(f"  ERROR fetching section: {exc}")
                continue

            soup = BeautifulSoup(html, "html.parser")
            product_urls = self._extract_product_links(soup, section_path)
            log(f"  Found {len(product_urls)} product links")

            for idx, url in enumerate(product_urls, start=1):
                if options["limit"] and total_imported >= options["limit"]:
                    break
                try:
                    product = self._parse_product(session, url, cat_obj, options["no_images"])
                except Exception as exc:
                    log(f"  Failed: {url} ({exc})")
                    continue
                total_imported += 1
                elapsed = max(1.0, time.time() - start_ts)
                rate = total_imported / elapsed
                remaining = max(0, len(product_urls) - idx)
                eta_min = int(remaining / rate) // 60 if rate > 0 else 0
                log(f"  [{idx}/{len(product_urls)}] total={total_imported} eta~{eta_min}m: {product.name}")
                time.sleep(options["sleep"])

        log(f"\nDone. Imported {total_imported} product cards from seal-tech.ru.")
        log_fp.close()

    # -----------------------------------------------------------------------
    # Link extractor
    # -----------------------------------------------------------------------

    def _extract_product_links(self, soup: BeautifulSoup, section_path: str) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for a in soup.find_all("a", href=True):
            path = _norm_path(a["href"])
            if not _is_product_url(path, section_path):
                continue
            if path in seen:
                continue
            seen.add(path)
            result.append(_full_url(path))
        return result

    # -----------------------------------------------------------------------
    # Product page parser
    # -----------------------------------------------------------------------

    def _parse_product(
        self,
        session: requests.Session,
        url: str,
        cat_obj: SealCategory,
        skip_images: bool,
    ) -> SealProduct:
        html = session.get(url, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")

        # --- Title ---
        h1 = soup.find("h1")
        title = _normalize_text(h1.get_text(" ", strip=True)) if h1 else ""
        if not title:
            og = soup.find("meta", property="og:title")
            title = _normalize_text(og.get("content", "") if og else "")
        if not title:
            raise ValueError("Missing product title")

        # --- Characteristics table ---
        # First <table> on the page — contains: Температура (min/max), Скорость, Давление, Материал
        attributes: list[dict] = []
        attrs_text_parts: list[str] = []
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")
            # First row is column headers, second row is sub-headers (min/max), rest are data
            headers: list[str] = []
            sub_headers: list[str] = []
            data_rows: list[list[str]] = []
            for i, row in enumerate(rows):
                cells = row.find_all(["th", "td"])
                texts = [_normalize_text(c.get_text(" ", strip=True)) for c in cells]
                if i == 0:
                    # Main headers (may have colspan)
                    expanded: list[str] = []
                    for cell in cells:
                        col = _normalize_text(cell.get_text(" ", strip=True))
                        span = int(cell.get("colspan", 1))
                        expanded.extend([col] * span)
                    headers = expanded
                elif i == 1 and any(t in ("min", "max", "") for t in texts):
                    # Sub-headers like min/max
                    sub_headers = texts
                else:
                    data_rows.append(texts)
            # Build combined column names
            col_names: list[str] = []
            for j, h in enumerate(headers):
                sub = sub_headers[j] if j < len(sub_headers) else ""
                if sub and sub not in ("", "-"):
                    col_names.append(f"{h} {sub}".strip())
                else:
                    col_names.append(h)
            # Build attributes from data rows
            for row_vals in data_rows:
                row_parts: list[str] = []
                for j, val in enumerate(row_vals):
                    if not val or val == "-":
                        continue
                    col = col_names[j] if j < len(col_names) else f"col{j+1}"
                    if col:
                        row_parts.append(f"{col}: {val}")
                if row_parts:
                    row_text = " | ".join(row_parts)
                    material = ""
                    for j, val in enumerate(row_vals):
                        if j < len(col_names) and "материал" in col_names[j].lower() and val and val != "-":
                            material = val
                            break
                    attr_name = f"Характеристики{' (' + material + ')' if material else ''}"
                    attributes.append({"name": attr_name, "value": row_text})
                    attrs_text_parts.append(row_text)

        # --- Description ---
        # All paragraphs that appear after the table (or anywhere in main content)
        description = ""
        desc_parts: list[str] = []
        # look for paragraphs in the main content area (skip nav/footer)
        main = soup.find("main") or soup.find("article") or soup.find(
            "div", class_=lambda c: c and any(
                kw in c for kw in ("content", "product", "detail", "text")
            )
        )
        if not main:
            main = soup
        for p in main.find_all("p"):
            text = _normalize_text(p.get_text(" ", strip=True))
            if len(text) > 40:
                desc_parts.append(text)
        description = _normalize_text("\n".join(desc_parts), keep_newlines=True)

        # --- Image ---
        # seal-tech stores images at /assets/images/
        image_url = ""
        # 1. og:image (most reliable)
        og_img = soup.find("meta", property="og:image")
        if og_img:
            image_url = og_img.get("content", "")
        # 2. First img with /assets/images/ in src
        if not image_url:
            img_tag = soup.find("img", src=lambda s: s and "/assets/images/" in s)
            if img_tag:
                image_url = _full_url(img_tag.get("src", ""))
        # 3. Any img with product code in src (derived from URL)
        if not image_url:
            code = url.rstrip("/").split("/")[-1].lower()
            img_tag = soup.find("img", src=lambda s: s and code in (s or "").lower())
            if img_tag:
                image_url = _full_url(img_tag.get("src", ""))

        # --- Save to DB ---
        product = SealProduct.objects.filter(source_url=url).first()
        if not product:
            slug = _unique_slug(SealProduct, title)
            product = SealProduct(source_url=url, slug=slug)

        product.name = title
        product.category = cat_obj
        product.subcategory = None  # profile cards have no subcategory
        product.image_url = image_url
        product.description = description
        product.attributes = attributes
        product.attributes_text = _normalize_text(" ".join(attrs_text_parts))
        product.is_active = True

        if image_url and not skip_images:
            try:
                img_resp = session.get(image_url, timeout=30)
                if img_resp.ok:
                    filename = image_url.split("/")[-1].split("?")[0] or "image.jpg"
                    product.image.save(filename, ContentFile(img_resp.content), save=False)
            except Exception:
                pass

        product.save()
        return product
