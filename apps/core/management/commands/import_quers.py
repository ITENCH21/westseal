"""
Import seal products from https://quers.ru/catalog/seals/

Only products under /catalog/seals/ are imported (seals / RTI products only).

Category structure:
  /catalog/seals/                          — root listing (7 categories)
  /catalog/seals/<cat>/                    — category page
  /catalog/seals/<cat>/<product>/          — product detail page

Product discovery uses the site sitemap:
  https://quers.ru/sitemap-iblock-12.xml  — lists all catalog URLs

Usage:
    python manage.py import_quers
    python manage.py import_quers --category a-seals
    python manage.py import_quers --limit 10 --no-images
    python manage.py import_quers --sleep 0.4 --log-file data/import_quers.log
"""
import re
import time
import urllib.parse
from html import unescape
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.core.models import SealCategory, SealProduct

BASE_URL = "https://quers.ru"
SEALS_PATH = "/catalog/seals/"
SEALS_URL = BASE_URL + SEALS_PATH
SITEMAP_URL = BASE_URL + "/sitemap-iblock-12.xml"

# Slug prefix to distinguish quers categories from other sources
SLUG_PREFIX = "quers-"


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _clean_url(url: str) -> str:
    return url.split("#")[0] if url else ""


def _full_url(href: str) -> str:
    if not href:
        return ""
    return urllib.parse.urljoin(BASE_URL, href)


def _norm_path(href: str) -> str:
    """Return clean path string from an href."""
    raw = _clean_url(href)
    return urllib.parse.urlparse(raw).path or raw


def _within_seals(path: str) -> bool:
    return path.startswith(SEALS_PATH)


def _is_category_url(path: str) -> bool:
    """Category URL: /catalog/seals/<cat>/ — exactly 3 segments."""
    if not _within_seals(path):
        return False
    parts = path.strip("/").split("/")
    # catalog / seals / <cat>  -> 3 parts
    return len(parts) == 3


def _is_product_url(path: str) -> bool:
    """Product URL: /catalog/seals/<cat>/<product>/ — exactly 4 segments."""
    if not _within_seals(path):
        return False
    parts = path.strip("/").split("/")
    # catalog / seals / <cat> / <product>  -> 4 parts
    return len(parts) == 4


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

def _normalize_text(value: str, *, keep_newlines: bool = False) -> str:
    if not value:
        return ""
    text = unescape(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = text.replace("\\n", "\n")
    text = re.sub(r"(?<=\d)\s*[×xХх]\s*(?=\d)", "x", text)
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r"\.\s*\.+", ".", text)
    if keep_newlines:
        text = "\n".join(re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.split("\n"))
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


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Import seal catalog from quers.ru (/catalog/seals/) into local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            help="Parse only one category slug as it appears on the site (e.g. a-seals)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit total products to import (0 = no limit)",
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip downloading images",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.5,
            help="Delay between requests (seconds)",
        )
        parser.add_argument(
            "--log-file",
            default="data/import_quers.log",
            help="Log file path",
        )

    def handle(self, *args, **options):
        log_path = options["log_file"]
        log_fp = open(log_path, "a", encoding="utf-8")

        def log(msg: str):
            self.stdout.write(msg)
            log_fp.write(msg + "\n")
            log_fp.flush()

        start_ts = time.time()
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; EURO-SEAL bot/2.0)",
                "Accept-Language": "ru,en;q=0.8",
            }
        )

        # --- Step 1: Discover product URLs from sitemap ---
        log(f"Fetching sitemap: {SITEMAP_URL}")
        sitemap_xml = session.get(SITEMAP_URL, timeout=30).text
        product_urls_by_cat = self._parse_sitemap(sitemap_xml)

        total_cats = len(product_urls_by_cat)
        total_urls = sum(len(v) for v in product_urls_by_cat.values())
        log(f"Sitemap: {total_cats} seal categories, {total_urls} product URLs total")

        if options["category"]:
            filtered = {k: v for k, v in product_urls_by_cat.items() if k == options["category"]}
            if not filtered:
                self.stdout.write(self.style.WARNING(
                    f"Category '{options['category']}' not found in sitemap. "
                    f"Available: {list(product_urls_by_cat.keys())}"
                ))
                return
            product_urls_by_cat = filtered

        # --- Step 2: Discover category names from the seals index page ---
        log("Fetching seals index for category names ...")
        html = session.get(SEALS_URL, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")
        cat_name_map = self._build_cat_name_map(soup)  # raw_slug → name
        log(f"Category names found: {len(cat_name_map)}")

        # --- Step 3: Upsert categories ---
        categories_map: dict[str, SealCategory] = {}
        for raw_slug in product_urls_by_cat:
            name = cat_name_map.get(raw_slug) or raw_slug.replace("-", " ").title()
            prefixed_slug = f"{SLUG_PREFIX}{raw_slug}"
            obj, _ = SealCategory.objects.get_or_create(
                slug=prefixed_slug,
                defaults={"name": name, "source_url": BASE_URL + SEALS_PATH + raw_slug + "/", "parent": None},
            )
            obj.name = name
            obj.source_url = BASE_URL + SEALS_PATH + raw_slug + "/"
            obj.parent = None
            obj.is_active = True
            obj.save(update_fields=["name", "source_url", "parent", "is_active"])
            categories_map[raw_slug] = obj
            log(f"  Category: {name}  slug={prefixed_slug}")

        # --- Step 4: Import products ---
        total_imported = 0

        for raw_slug, urls in product_urls_by_cat.items():
            cat_obj = categories_map[raw_slug]
            log(f"\nImporting category: {cat_obj.name} ({len(urls)} products)")

            for idx, url in enumerate(urls, start=1):
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
                remaining = max(0, len(urls) - idx)
                eta_sec = int(remaining / rate) if rate > 0 else 0
                eta_min = eta_sec // 60
                log(f"  [{idx}/{len(urls)}] total={total_imported} eta~{eta_min}m: {product.name}")
                time.sleep(options["sleep"])

            if options["limit"] and total_imported >= options["limit"]:
                break

        log(f"\nDone. Imported {total_imported} products from quers.ru.")
        log_fp.close()

    # -----------------------------------------------------------------------
    # Sitemap parser + category name extractor
    # -----------------------------------------------------------------------

    def _parse_sitemap(self, xml_text: str) -> dict[str, list[str]]:
        """
        Parse sitemap XML and return {raw_cat_slug: [product_url, ...]}
        for all product URLs under /catalog/seals/<cat>/<product>/.
        """
        result: dict[str, list[str]] = {}
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError:
            return result
        # Handle namespace
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"
        for url_el in root.findall(f"{ns}url"):
            loc_el = url_el.find(f"{ns}loc")
            if loc_el is None or not loc_el.text:
                continue
            loc = loc_el.text.strip()
            path = urllib.parse.urlparse(loc).path
            if not _is_product_url(path):
                continue
            parts = path.strip("/").split("/")
            # parts: catalog / seals / <cat> / <product>
            cat_raw = parts[2]
            result.setdefault(cat_raw, []).append(loc)
        return result

    def _build_cat_name_map(self, soup: BeautifulSoup) -> dict[str, str]:
        """Return {raw_slug: human_name} for all /catalog/seals/<cat>/ links."""
        result: dict[str, str] = {}
        for a in soup.select('a[href*="/catalog/seals/"]'):
            path = _norm_path(a.get("href", ""))
            if not _is_category_url(path):
                continue
            raw_slug = path.strip("/").split("/")[2]
            name = self._extract_category_name(a)
            if name and raw_slug not in result:
                result[raw_slug] = name
        return result

    def _extract_category_name(self, a_tag) -> str:
        """Extract only the category name from a link tag, without description text."""
        # Try: title attribute
        if a_tag.get("title"):
            return _normalize_text(a_tag["title"])
        # Full text but split at CamelCase boundary (русский + латиница)
        # e.g. "Опорные кольцаСлужат в качестве" → "Опорные кольца"
        full = a_tag.get_text(strip=True)
        parts = re.split(r"(?<=[а-яёa-z])(?=[А-ЯЁA-Z])", full, maxsplit=1)
        return _normalize_text(parts[0])

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
            title = _normalize_text(og["content"] if og else "")
        if not title:
            raise ValueError("Missing product title")

        # --- Description ---
        # quers.ru has a descriptive paragraph right below h1/product info block
        description = ""
        # Try: div with class containing "detail-text" or "product-detail" style blocks
        for sel in [".detail-text", ".product-detail-text", ".bx-text", ".catalog-element-description"]:
            el = soup.select_one(sel)
            if el:
                description = _normalize_text(el.get_text("\n", strip=True), keep_newlines=True)
                break
        if not description:
            # Fallback: collect paragraph text that's near the product title section
            # Look for paragraphs that contain descriptive content (not nav/footer)
            main_content = soup.select_one("main, .catalog-element, .bx-soa-section, article")
            if not main_content:
                main_content = soup
            paras = []
            for p in main_content.find_all("p"):
                text = p.get_text(strip=True)
                # Skip very short, or navigation-like paragraphs
                if len(text) > 60:
                    paras.append(text)
                if len(paras) >= 3:
                    break
            description = _normalize_text("\n".join(paras), keep_newlines=True)

        # --- Attributes / properties ---
        # quers.ru product pages have tables:
        #   "Таблица применяемости материалов" — materials/temperature/speed/pressure
        #   "Рекомендации к размерам уплотняемых деталей" — dimensions table
        attributes: list[dict] = []
        attrs_text_parts: list[str] = []

        # Find all tables on the page and extract their content
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue
            # Get header text from preceding heading if any
            table_heading = ""
            prev = table.find_previous_sibling(["h2", "h3", "h4"])
            if prev:
                table_heading = _normalize_text(prev.get_text(" ", strip=True))

            # Parse header row to get column names
            header_row = rows[0]
            headers = [_normalize_text(th.get_text(" ", strip=True)) for th in header_row.find_all(["th", "td"])]
            if not any(headers):
                continue

            # If there are actual data rows, use them
            data_rows = rows[1:] if rows[0].find("th") else rows
            for row in data_rows:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                # Build a combined attribute string: "col1=val1 col2=val2 ..."
                row_parts = []
                row_dict_values = []
                for i, cell in enumerate(cells):
                    val = _normalize_text(cell.get_text(" ", strip=True))
                    if not val or val == headers[i] if i < len(headers) else False:
                        continue
                    col = headers[i] if i < len(headers) else f"col{i+1}"
                    if col and val:
                        row_parts.append(f"{col}: {val}")
                        row_dict_values.append(f"{val}")
                if row_parts:
                    row_label = " | ".join(row_dict_values)
                    attr_name = table_heading if table_heading else "Характеристики"
                    attributes.append({"name": attr_name, "value": row_label})
                    attrs_text_parts.append(" ".join(row_parts))

        # Also try mkt-rti style table.props_list (fallback)
        if not attributes:
            for row in soup.select("table.props_list tr"):
                name_el = row.select_one(".char_name")
                value_el = row.select_one(".char_value")
                if name_el and value_el:
                    n = _normalize_text(name_el.get_text(" ", strip=True))
                    v = _normalize_text(value_el.get_text(" ", strip=True))
                    if n:
                        attributes.append({"name": n, "value": v})
                        attrs_text_parts.append(f"{n} {v}")

        # --- Image ---
        # quers.ru stores the main product image at /upload/pics/ (high-res)
        image_url = ""
        # 1. Try og:image (most reliable)
        og_img = soup.find("meta", property="og:image")
        if og_img:
            image_url = og_img.get("content", "")
        # 2. Fallback: first img with /upload/pics/ in src
        if not image_url:
            pics_img = soup.find("img", src=lambda s: s and "/upload/pics/" in s)
            if pics_img:
                image_url = _full_url(pics_img.get("src", ""))
        # 3. Fallback: first img with /upload/iblock/ in src
        if not image_url:
            iblock_img = soup.find("img", src=lambda s: s and "/upload/iblock/" in s)
            if iblock_img:
                image_url = _full_url(iblock_img.get("src", ""))

        # --- Save to DB ---
        product = SealProduct.objects.filter(source_url=url).first()
        if not product:
            slug = _unique_slug(SealProduct, title)
            product = SealProduct(source_url=url, slug=slug)

        product.name = title
        product.category = cat_obj
        product.subcategory = None  # quers.ru has no subcategories
        product.image_url = image_url
        product.description = description
        product.attributes = attributes
        product.attributes_text = _normalize_text(" ".join(attrs_text_parts))
        product.is_active = True

        if image_url and not skip_images:
            try:
                img_resp = session.get(image_url, timeout=30)
                if img_resp.ok:
                    filename = image_url.split("/")[-1].split("?")[0] or "image.png"
                    product.image.save(filename, ContentFile(img_resp.content), save=False)
            except Exception:
                pass

        product.save()
        return product
