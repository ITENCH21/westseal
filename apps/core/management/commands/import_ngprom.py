"""
Import sized seal products from https://ng-prom.ru/uplotnenia/

Each product page contains type (e.g. KDSP), dimensions (OD, ID, height),
material, speed, pressure, temperature — all are valuable for SEO.
Prices are intentionally NOT imported.

Sections:
  /uplotnenia/uplotnenia-porsna                     → uplotnenija_porshnja
  /uplotnenia/uplotnenia-stoka                      → uplotnenija_shtoka
  /uplotnenia/grazesemniki                          → grjazesemniki
  /uplotnenia/napravlausie-kolca                    → napravljajuwie_gidrocilindrov
  /uplotnenia/staticeskie-uplotnenie-rezinovye-kolca → kolca_uplatnitelnye
  /pnevmaticeskie-uplotnenia                        → pnevmaticheskoe_uplotnenija

Images:
  ALL ng-prom.ru product photos contain a burned-in watermark with their logo.
  Instead of downloading watermarked images we always use our own logo
  (static/img/logo-blue.png) as the product image.
  The original image URL is still stored in image_url for reference.

Usage:
    python manage.py import_ngprom
    python manage.py import_ngprom --section uplotnenia-porsna --limit 20
    python manage.py import_ngprom --pages 5 --sleep 1.5
"""
import re
import time
import urllib.parse
from html import unescape
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.core.models import SealCategory, SealProduct

BASE_URL = "https://ng-prom.ru"
SLUG_PREFIX = "ngprom-"

# Path to fallback logo (used when image has watermark or is unavailable)
LOGO_PATH = Path(settings.BASE_DIR) / "static" / "img" / "logo-blue.png"

SECTIONS = [
    ("uplotnenia-porsna",   "/uplotnenia/uplotnenia-porsna",                       "uplotnenija_porshnja"),
    ("uplotnenia-stoka",    "/uplotnenia/uplotnenia-stoka",                        "uplotnenija_shtoka"),
    ("grazesemniki",        "/uplotnenia/grazesemniki",                            "grjazesemniki"),
    ("napravlausie-kolca",  "/uplotnenia/napravlausie-kolca",                      "napravljajuwie_gidrocilindrov"),
    ("staticeskie",         "/uplotnenia/staticeskie-uplotnenie-rezinovye-kolca",  "kolca_uplatnitelnye"),
    ("pnevmatika",          "/pnevmaticeskie-uplotnenia",                          "pnevmaticheskoe_uplotnenija"),
]

# Characteristics to import (lower-cased key contains this → use as attribute name)
ATTR_INCLUDE = re.compile(
    r"тип|material|материал|наружн|внутренн|высот|скорость|температур|давление|"
    r"бренд|brand|полное|артикул|страна",
    re.I,
)
# Characteristics to SKIP (price / stock / package data)
ATTR_SKIP = re.compile(
    r"цена|стоимость|количество|наличие|склад|длина.*упак|ширина.*упак|"
    r"высот.*упак|вес|код товара",
    re.I,
)


def _load_logo_content() -> bytes:
    """Return the bytes of our logo (used instead of watermarked ng-prom images)."""
    if LOGO_PATH.exists():
        return LOGO_PATH.read_bytes()
    return b""

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
    help = "Import sized seal products from ng-prom.ru (type + dimensions, no prices)"

    def add_arguments(self, parser):
        parser.add_argument("--section",  help="Only import one section key (e.g. uplotnenia-porsna)")
        parser.add_argument("--pages",    type=int, default=0,   help="Max listing pages per section (0 = all)")
        parser.add_argument("--limit",    type=int, default=0,   help="Max total products to import")
        parser.add_argument("--sleep",    type=float, default=1.0)
        parser.add_argument("--log-file", default="data/import_ngprom.log")

    def handle(self, *args, **options):
        log_fp = open(options["log_file"], "a", encoding="utf-8")

        def log(msg: str) -> None:
            self.stdout.write(msg)
            log_fp.write(msg + "\n")
            log_fp.flush()

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; WESTSEAL bot/2.0)",
            "Accept-Language": "ru,en;q=0.8",
        })

        logo_bytes = _load_logo_content()
        if not logo_bytes:
            log("WARNING: logo-blue.png not found — products will have no image")

        sections = SECTIONS
        if options["section"]:
            sections = [s for s in SECTIONS if s[0] == options["section"]]
            if not sections:
                self.stdout.write(self.style.WARNING(
                    f"Unknown section. Available: {', '.join(s[0] for s in SECTIONS)}"
                ))
                return

        total_imported = 0
        total_logo_used = 0

        for slug_key, url_path, db_slug in sections:
            cat = SealCategory.objects.filter(slug=db_slug, is_active=True).first()
            if not cat:
                log(f"WARNING: category not found: {db_slug!r} — skipping")
                continue

            log(f"\nSection: {slug_key} → {cat.name}")

            page_num  = 1
            max_pages = options["pages"] or 99999

            while page_num <= max_pages:
                if options["limit"] and total_imported >= options["limit"]:
                    break

                page_url = BASE_URL + url_path + (f"?page={page_num}" if page_num > 1 else "")
                log(f"  Page {page_num}: {page_url}")

                try:
                    html = session.get(page_url, timeout=30).text
                except Exception as exc:
                    log(f"  ERROR fetching listing: {exc}")
                    break

                soup = BeautifulSoup(html, "html.parser")
                product_links = self._extract_product_links(soup, url_path)

                if not product_links:
                    log("  No product links found — end of section")
                    break

                for idx, purl in enumerate(product_links, 1):
                    if options["limit"] and total_imported >= options["limit"]:
                        break
                    try:
                        product, logo_used = self._parse_and_save(
                            session, purl, cat, logo_bytes
                        )
                    except Exception as exc:
                        log(f"    FAIL {purl}: {exc}")
                        continue

                    total_imported += 1
                    if logo_used:
                        total_logo_used += 1
                    flag = " [logo]" if logo_used else ""
                    log(f"    [{idx}/{len(product_links)}] {product.name}{flag}  (total={total_imported})")
                    time.sleep(options["sleep"])

                # Check for next page
                if not self._has_next_page(soup, page_num):
                    break
                page_num += 1

        log(f"\nDone. Imported {total_imported} products from ng-prom.ru "
            f"(logo used for {total_logo_used} images)")
        log_fp.close()

    # ─────────────────────────────────────────────── listing page helpers ─ #

    def _extract_product_links(self, soup: BeautifulSoup, url_path: str) -> list[str]:
        seen, result = set(), []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            path = urllib.parse.urlparse(href).path
            if not path.startswith("/goods/"):
                continue
            if path in seen:
                continue
            seen.add(path)
            result.append(BASE_URL + path)
        return result

    def _has_next_page(self, soup: BeautifulSoup, current: int) -> bool:
        """Return True if a link to page current+1 exists."""
        for a in soup.find_all("a", href=True):
            if f"page={current + 1}" in a["href"]:
                return True
        return False

    # ────────────────────────────────────────────────── product page ──────── #

    def _parse_and_save(
        self,
        session: requests.Session,
        url: str,
        cat: SealCategory,
        logo_bytes: bytes,
    ) -> tuple["SealProduct", bool]:
        html = session.get(url, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")

        # ── title ─────────────────────────────────────────────────────────── #
        h1 = soup.find("h1")
        title = _norm(h1.get_text(" ", strip=True)) if h1 else ""
        if not title:
            og = soup.find("meta", property="og:title")
            title = _norm(og.get("content", "")) if og else ""
        if not title:
            raise ValueError("no title")

        # ── characteristics table ─────────────────────────────────────────── #
        attributes: list[dict] = []
        attrs_text_parts: list[str] = []
        description_parts: list[str] = []

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["th", "td"])
                if len(cells) != 2:
                    continue
                key   = _norm(cells[0].get_text(" ", strip=True))
                value = _norm(cells[1].get_text(" ", strip=True))
                if not key or not value:
                    continue
                if ATTR_SKIP.search(key):
                    continue
                if ATTR_INCLUDE.search(key):
                    attributes.append({"name": key, "value": value})
                    attrs_text_parts.append(f"{key}: {value}")

        # ── description from "Описание" tab / block ───────────────────────── #
        for block in soup.find_all(class_=re.compile(r"descr|content|tab", re.I)):
            t = _norm(block.get_text(" ", strip=True))
            if len(t) > 80:
                description_parts.append(t[:1000])
                break

        description = "\n".join(description_parts)

        # ── image ─────────────────────────────────────────────────────────── #
        # ng-prom.ru burns their logo watermark into every product photo.
        # We store the original URL for reference but always use our own logo.
        image_url = ""
        og_img = soup.find("meta", property="og:image")
        if og_img:
            image_url = og_img.get("content", "")
        if not image_url:
            img_tag = soup.find("img", src=re.compile(r"/files/images/cache/Goods/", re.I))
            if img_tag:
                src = img_tag.get("src", "")
                image_url = src if src.startswith("http") else urllib.parse.urljoin(BASE_URL, src)

        # ── save ──────────────────────────────────────────────────────────── #
        obj = SealProduct.objects.filter(source_url=url).first()
        if not obj:
            obj = SealProduct(source_url=url, slug=_unique_slug(title))

        obj.name           = title
        obj.name_en        = title
        obj.category       = cat
        obj.subcategory    = None
        obj.image_url      = image_url
        obj.description    = description
        obj.attributes     = attributes
        obj.attributes_text = " | ".join(attrs_text_parts)
        obj.is_active      = True

        # Always save our logo as the product image (ng-prom images are watermarked)
        if logo_bytes and not obj.pk:  # only on first create, don't re-save on update
            obj.image.save("logo-blue.png", ContentFile(logo_bytes), save=False)

        obj.save()
        return obj, True
