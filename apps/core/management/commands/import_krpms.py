"""
Import seal products from https://www.krpms.ru/catalog/uplotneniya/

Only products under /catalog/uplotneniya/ are imported (seals only).
Cylinders, hoses, tubes and rods are skipped.

Usage:
    python manage.py import_krpms
    python manage.py import_krpms --category gryazesemniki
    python manage.py import_krpms --limit 10 --no-images
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

BASE_URL = "https://www.krpms.ru"
SEALS_PATH = "/catalog/uplotneniya/"
SEALS_URL = BASE_URL + SEALS_PATH

# Slug prefix to distinguish krpms categories from mkt-rti ones
SLUG_PREFIX = "krpms-"


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


def _is_product_url(path: str) -> bool:
    """Product URL: under /catalog/uplotneniya/ and ends with .html"""
    if not _within_seals(path):
        return False
    return path.endswith(".html")


def _is_level2_category(path: str) -> bool:
    """e.g. /catalog/uplotneniya/gryazesemniki/"""
    if not _within_seals(path) or _is_product_url(path):
        return False
    parts = path.strip("/").split("/")
    # catalog / uplotneniya / <cat>  -> 3 parts
    return len(parts) == 3


def _is_level3_category(path: str) -> bool:
    """e.g. /catalog/uplotneniya/gryazesemniki/gryazesemniki-kastas/"""
    if not _within_seals(path) or _is_product_url(path):
        return False
    parts = path.strip("/").split("/")
    # catalog / uplotneniya / <cat> / <subcat>  -> 4 parts
    return len(parts) == 4


# ---------------------------------------------------------------------------
# Text normalisation (same approach as import_mkt_rti)
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
    help = "Import seal catalog from krpms.ru (uplotneniya section) into local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            help="Parse only one level-2 category slug (e.g. gryazesemniki)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit total products to import (0 = no limit)",
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=0,
            help="Limit pages per category (0 = no limit)",
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
            default="data/import_krpms.log",
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

        log("Fetching uplotneniya index from krpms.ru ...")
        html = session.get(SEALS_URL, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")
        cat_links = self._extract_level2_categories(soup)
        log(f"Found level-2 seal categories: {len(cat_links)}")

        if options["category"]:
            cat_links = [c for c in cat_links if c["slug"] == options["category"]]
            if not cat_links:
                self.stdout.write(self.style.WARNING("Category slug not found on index."))
                return

        # Upsert level-2 categories directly at top level (parent=None)
        categories_map: dict[str, SealCategory] = {}
        for cat in cat_links:
            obj, _ = SealCategory.objects.get_or_create(
                slug=cat["slug"],
                defaults={
                    "name": cat["name"],
                    "source_url": cat["url"],
                    "parent": None,
                },
            )
            obj.name = cat["name"]
            obj.source_url = cat["url"]
            obj.parent = None
            obj.is_active = True
            obj.save(update_fields=["name", "source_url", "parent", "is_active"])
            categories_map[cat["raw_slug"]] = obj

        total_imported = 0

        for cat in cat_links:
            if options["limit"] and total_imported >= options["limit"]:
                break

            cat_obj = categories_map[cat["raw_slug"]]
            subcategories: dict[str, SealCategory] = {}
            seen: set[str] = set()

            log(f"\nParsing category: {cat['name']} ({cat['url']})")

            def import_url(url: str, idx: int | None = None, total: int | None = None):
                nonlocal total_imported
                if url in seen:
                    return
                seen.add(url)
                if options["limit"] and total_imported >= options["limit"]:
                    return
                try:
                    product = self._parse_product(
                        session, url, cat_obj, subcategories, options["no_images"]
                    )
                except Exception as exc:
                    log(f"  Failed: {url} ({exc})")
                    return
                total_imported += 1
                elapsed = max(1.0, time.time() - start_ts)
                rate = total_imported / elapsed
                if total:
                    remaining = max(0, total - (idx or 0))
                    eta_sec = int(remaining / rate) if rate > 0 else 0
                    eta_min = eta_sec // 60
                    log(f"  Imported [{idx}/{total}] total={total_imported} eta~{eta_min}m: {product.name}")
                else:
                    log(f"  Imported total={total_imported}: {product.name}")
                time.sleep(options["sleep"])

            # Crawl category pages, discover subcategories and direct products
            for page_url, page_html in self._crawl_pages(session, cat["url"], options["max_pages"]):
                log(f"  Category page: {page_url}")
                page_soup = BeautifulSoup(page_html, "html.parser")

                # Discover level-3 subcategory links
                for sub in self._extract_level3_categories(page_soup, cat["raw_slug"]):
                    if sub["raw_slug"] in subcategories:
                        continue
                    subcat_slug = f"{SLUG_PREFIX}{cat['raw_slug']}-{sub['raw_slug']}"
                    obj, _ = SealCategory.objects.get_or_create(
                        slug=subcat_slug,
                        defaults={
                            "name": sub["name"],
                            "code": sub["raw_slug"].upper(),
                            "parent": cat_obj,
                            "source_url": sub["url"],
                        },
                    )
                    obj.name = sub["name"] or obj.name
                    obj.code = sub["raw_slug"].upper()
                    obj.parent = cat_obj
                    obj.source_url = sub["url"]
                    obj.is_active = True
                    obj.save(update_fields=["name", "code", "parent", "source_url", "is_active"])
                    subcategories[sub["raw_slug"]] = obj

                # Collect direct product links on this category page
                for url in self._extract_product_links(page_soup):
                    import_url(url)
                    if options["limit"] and total_imported >= options["limit"]:
                        break

                if options["limit"] and total_imported >= options["limit"]:
                    break

            # Crawl subcategory pages
            for sub_obj in subcategories.values():
                if options["limit"] and total_imported >= options["limit"]:
                    break
                page_idx = 0
                for page_url, sub_html in self._crawl_pages(session, sub_obj.source_url, options["max_pages"]):
                    page_idx += 1
                    log(f"  Subcategory {sub_obj.name}: page {page_idx} {page_url}")
                    sub_soup = BeautifulSoup(sub_html, "html.parser")
                    collected = list(self._extract_product_links(sub_soup))
                    for idx, url in enumerate(collected, start=1):
                        if options["limit"] and total_imported >= options["limit"]:
                            break
                        import_url(url, idx, len(collected))
                    if options["limit"] and total_imported >= options["limit"]:
                        break

        log(f"\nDone. Imported {total_imported} products from krpms.ru.")
        log_fp.close()

    # -----------------------------------------------------------------------
    # Link extractors
    # -----------------------------------------------------------------------

    def _extract_level2_categories(self, soup: BeautifulSoup) -> list[dict]:
        """Return categories directly under /catalog/uplotneniya/."""
        items: dict[str, dict] = {}
        for a in soup.select('a[href*="/catalog/uplotneniya/"]'):
            path = _norm_path(a.get("href", ""))
            if not _is_level2_category(path):
                continue
            name = a.get_text(strip=True)
            if not name:
                continue
            raw_slug = path.strip("/").split("/")[2]  # e.g. "gryazesemniki"
            prefixed_slug = f"{SLUG_PREFIX}{raw_slug}"
            items[raw_slug] = {
                "name": name,
                "raw_slug": raw_slug,
                "slug": prefixed_slug,
                "url": _full_url(path),
            }
        return list(items.values())

    def _extract_level3_categories(self, soup: BeautifulSoup, parent_raw_slug: str) -> list[dict]:
        """Return subcategories one level under the given category."""
        items: dict[str, dict] = {}
        for a in soup.select('a[href*="/catalog/uplotneniya/"]'):
            path = _norm_path(a.get("href", ""))
            if not _is_level3_category(path):
                continue
            parts = path.strip("/").split("/")
            if parts[2] != parent_raw_slug:
                continue
            raw_slug = parts[3]
            name = a.get_text(strip=True) or raw_slug.upper()
            items[raw_slug] = {
                "name": name,
                "raw_slug": raw_slug,
                "url": _full_url(path),
            }
        return list(items.values())

    def _extract_product_links(self, soup: BeautifulSoup) -> Iterable[str]:
        """Yield absolute product URLs found in a page."""
        seen_paths: set[str] = set()
        for a in soup.select('a[href*="/catalog/uplotneniya/"]'):
            path = _norm_path(a.get("href", ""))
            if not _is_product_url(path):
                continue
            if path in seen_paths:
                continue
            seen_paths.add(path)
            yield _full_url(path)

    # -----------------------------------------------------------------------
    # Pagination crawler (PAGEN_1 style — same as mkt-rti.ru)
    # -----------------------------------------------------------------------

    def _crawl_pages(
        self,
        session: requests.Session,
        start_url: str,
        max_pages: int,
    ) -> Iterable[tuple[str, str]]:
        base = start_url.split("?")[0]
        queue = [start_url]
        seen: set[str] = set()
        while queue:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                html = session.get(url, timeout=30).text
            except Exception:
                continue
            yield url, html
            if max_pages and len(seen) >= max_pages:
                break
            # Discover pagination links (PAGEN_*)
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if "PAGEN_" not in href:
                    continue
                full = _full_url(href) if not href.startswith("?") else base + href
                parsed = urllib.parse.urlparse(full)
                if parsed.path != urllib.parse.urlparse(base).path:
                    continue
                q = urllib.parse.parse_qs(parsed.query)
                page_params = {k: v[-1] for k, v in q.items() if k.startswith("PAGEN_") and v}
                if not page_params:
                    continue
                canonical = base + "?" + urllib.parse.urlencode(page_params)
                if canonical not in seen:
                    queue.append(canonical)

    # -----------------------------------------------------------------------
    # Product page parser
    # -----------------------------------------------------------------------

    def _parse_product(
        self,
        session: requests.Session,
        url: str,
        cat_obj: SealCategory,
        sub_map: dict[str, SealCategory],
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
        # krpms uses a div/section after an h2 "Описание"
        description = ""
        for heading in soup.find_all(["h2", "h3"]):
            if re.search(r"описание", heading.get_text(), re.IGNORECASE):
                # gather all text siblings until next heading
                parts = []
                for sib in heading.find_next_siblings():
                    if sib.name in ("h1", "h2", "h3"):
                        break
                    parts.append(sib.get_text("\n", strip=True))
                description = _normalize_text("\n".join(parts), keep_newlines=True)
                break
        if not description:
            # fallback: div#descr (mkt-rti style — unlikely but safe)
            desc_el = soup.select_one("div#descr")
            if desc_el:
                description = _normalize_text(desc_el.get_text("\n", strip=True), keep_newlines=True)

        # --- Attributes / properties ---
        attributes: list[dict] = []
        attrs_text_parts: list[str] = []

        # Method 1: mkt-rti style table.props_list
        for row in soup.select("table.props_list tr"):
            name_el = row.select_one(".char_name")
            value_el = row.select_one(".char_value")
            if name_el and value_el:
                n = _normalize_text(name_el.get_text(" ", strip=True))
                v = _normalize_text(value_el.get_text(" ", strip=True))
                if n:
                    attributes.append({"name": n, "value": v})
                    attrs_text_parts.append(f"{n} {v}")

        # Method 2: krpms "Общие свойства" section — look for a table or dl
        if not attributes:
            for heading in soup.find_all(["h2", "h3"]):
                if re.search(r"свойств|характеристик|параметр", heading.get_text(), re.IGNORECASE):
                    container = heading.find_next_sibling()
                    if container is None:
                        continue
                    # Try <table>
                    table = container if container.name == "table" else container.find("table")
                    if table:
                        for row in table.find_all("tr"):
                            cells = row.find_all(["td", "th"])
                            if len(cells) >= 2:
                                n = _normalize_text(cells[0].get_text(" ", strip=True))
                                v = _normalize_text(cells[1].get_text(" ", strip=True))
                                if n:
                                    attributes.append({"name": n, "value": v})
                                    attrs_text_parts.append(f"{n} {v}")
                        break
                    # Try <ul>/<li> with colon separator
                    for li in container.find_all("li"):
                        text = li.get_text(" ", strip=True)
                        if ":" in text:
                            n, _, v = text.partition(":")
                            n = _normalize_text(n)
                            v = _normalize_text(v)
                            if n:
                                attributes.append({"name": n, "value": v})
                                attrs_text_parts.append(f"{n} {v}")
                    if attributes:
                        break

        # Method 3: generic — look for any dl (dt/dd pairs)
        if not attributes:
            for dl in soup.find_all("dl"):
                dts = dl.find_all("dt")
                dds = dl.find_all("dd")
                for dt, dd in zip(dts, dds):
                    n = _normalize_text(dt.get_text(" ", strip=True))
                    v = _normalize_text(dd.get_text(" ", strip=True))
                    if n:
                        attributes.append({"name": n, "value": v})
                        attrs_text_parts.append(f"{n} {v}")
                if attributes:
                    break

        # --- Image ---
        # krpms.ru stores product images inside iblock directories.
        # Skip logo/template images – they contain "local/templates/" in the path.
        def _is_logo(url: str) -> bool:
            return "local/templates/" in url or "/img/krpms" in url

        image_url = ""
        img_tag = soup.select_one(".production-detail-image img, .production-detail img[src*='/iblock/']")
        if img_tag:
            candidate = _full_url(img_tag.get("src", ""))
            if not _is_logo(candidate):
                image_url = candidate
        if not image_url:
            # fallback: first img with /iblock/ in src
            iblock_img = soup.find("img", src=lambda s: s and "/iblock/" in s)
            if iblock_img:
                candidate = _full_url(iblock_img.get("src", ""))
                if not _is_logo(candidate):
                    image_url = candidate
        # NOTE: do NOT use og:image fallback – krpms og:image is the site logo

        # --- Save to DB ---
        product = SealProduct.objects.filter(source_url=url).first()
        if not product:
            slug = _unique_slug(SealProduct, title)
            product = SealProduct(source_url=url, slug=slug)

        product.name = title
        product.category = cat_obj
        product.subcategory = self._infer_subcategory(url, sub_map)
        product.image_url = image_url
        product.description = description
        product.attributes = attributes
        product.attributes_text = _normalize_text(" ".join(attrs_text_parts))
        product.is_active = True

        if image_url and not skip_images:
            try:
                img_resp = session.get(image_url, timeout=30)
                if img_resp.ok:
                    filename = image_url.split("/")[-1].split("?")[0] or "image.webp"
                    product.image.save(filename, ContentFile(img_resp.content), save=False)
            except Exception:
                pass

        product.save()
        return product

    def _infer_subcategory(self, url: str, sub_map: dict[str, SealCategory]) -> SealCategory | None:
        """Map product URL to its level-3 subcategory if present."""
        path = urllib.parse.urlparse(url).path.strip("/").split("/")
        # path: catalog / uplotneniya / <cat> / <subcat> / product.html
        if len(path) >= 5:
            raw_slug = path[3]
            return sub_map.get(raw_slug)
        return None
