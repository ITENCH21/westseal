"""
Import seal products from https://spb-rezina.ru — OpenCart-based catalog.

Site structure:
  Category list:  /index.php?route=product/category&path=4
  Subcategory:    /index.php?route=product/category&path=4_<sub_id>&page=N
  Product page:   /index.php?route=product/product&path=4_<sub_id>&product_id=<id>

Usage:
    python manage.py import_spbrezina
    python manage.py import_spbrezina --path-id 4_446 --limit 20 --no-images
    python manage.py import_spbrezina --sleep 0.5 --log-file data/import_spbrezina.log
"""
import re
import time
from html import unescape
from typing import Iterator

import requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.core.models import SealCategory, SealProduct

BASE_URL = "https://spb-rezina.ru"

# Subcategories of path=4 that we want (id → db_category_slug, display_name).
# Skipped: Втулки кабельные (7292), Звёздочки (18648), Кольца и втулки МУВП (923)
SUBCATEGORY_MAP = {
    "18735": ("o-kolca",             "О-кольца USIT"),
    "1764":  ("o-kolca",             "О-кольца"),
    "18646": ("salniki",             "Сальники"),
    "18649": ("gidravlicheskie",     "Гидравлические манжеты"),
    "446":   ("pnevmaticheskie",     "Пневматические манжеты"),
    "916":   ("grjazesemniki",       "Грязесъемники"),
    "18702": ("v-ring",              "V-Ring"),
    "18675": ("manzhety",            "Манжеты БХ"),
}

# Rows to skip in attribute table (not product specs)
SKIP_ATTR_NAMES = {"розница", "мелкий опт", "опт", "наличие", "цена", "количество", "добавить"}

# Logo/placeholder image markers to skip
SKIP_IMAGE_FRAGMENTS = ["no_image", "no-image", "noimage", "placeholder"]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9",
    })
    return s


def _clean(text: str) -> str:
    """Basic text normalisation."""
    text = unescape(text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def _clean_title(title: str) -> str:
    """Normalise product title: collapse extra spaces and ГОСТ-style double spaces."""
    return re.sub(r"\s{2,}", " ", _clean(title))


def _unique_slug(base: str) -> str:
    base_slug = slugify(base) or "item"
    slug = base_slug
    i = 2
    while SealProduct.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{i}"
        i += 1
    return slug


def _get_or_create_category(slug: str, name: str) -> SealCategory:
    obj, created = SealCategory.objects.get_or_create(
        slug=slug,
        defaults={"name": name, "is_active": True},
    )
    if not created and not obj.is_active:
        obj.is_active = True
        obj.save(update_fields=["is_active"])
    return obj


class Command(BaseCommand):
    help = "Import seal products from spb-rezina.ru"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path-id",
            default="",
            help="Import only one sub-path like '4_446'. Default: all mapped subcategories.",
        )
        parser.add_argument("--limit", type=int, default=0, help="Stop after N products total")
        parser.add_argument("--max-pages", type=int, default=0, help="Max pages per subcategory (0=all)")
        parser.add_argument("--no-images", action="store_true", help="Skip image downloads")
        parser.add_argument("--sleep", type=float, default=0.5, help="Pause between requests (sec)")
        parser.add_argument("--log-file", default="data/import_spbrezina.log")

    def handle(self, *args, **options):
        log_fp = open(options["log_file"], "a", encoding="utf-8")

        def log(msg: str):
            self.stdout.write(msg)
            log_fp.write(msg + "\n")
            log_fp.flush()

        session = _session()
        start = time.time()
        total = 0

        # Determine which sub-paths to crawl
        if options["path_id"]:
            # e.g. "4_446" → sub_id = "446"
            raw = options["path_id"]
            parts = raw.split("_")
            sub_id = parts[-1]
            if sub_id not in SUBCATEGORY_MAP:
                log(f"Unknown path_id '{raw}'. Known sub_ids: {list(SUBCATEGORY_MAP)}")
                return
            targets = {sub_id: SUBCATEGORY_MAP[sub_id]}
        else:
            targets = SUBCATEGORY_MAP

        for sub_id, (cat_slug, cat_name) in targets.items():
            if options["limit"] and total >= options["limit"]:
                break

            cat_obj = _get_or_create_category(cat_slug, cat_name)
            path = f"4_{sub_id}"
            log(f"\n→ Subcategory: {cat_name} (path={path})")

            seen_products: set[str] = set()

            for page_url, page_html in self._crawl_pages(session, path, options["max_pages"]):
                log(f"  Page: {page_url}")
                soup = BeautifulSoup(page_html, "html.parser")
                product_urls = list(self._extract_product_urls(soup))

                if not product_urls:
                    log("  No products found on page — stopping.")
                    break

                for url in product_urls:
                    if url in seen_products:
                        continue
                    seen_products.add(url)

                    if options["limit"] and total >= options["limit"]:
                        break

                    try:
                        product = self._parse_product(session, url, cat_obj, options["no_images"])
                        total += 1
                        elapsed = max(1.0, time.time() - start)
                        rate = total / elapsed
                        log(f"  [{total}] {product.name[:70]}")
                    except Exception as exc:
                        log(f"  SKIP {url} — {exc}")

                    time.sleep(options["sleep"])

                if options["limit"] and total >= options["limit"]:
                    break

        log(f"\nDone. Imported {total} products.")
        log_fp.close()

    # ──────────────────────────────────────────────────────────────────
    # URL / page crawling
    # ──────────────────────────────────────────────────────────────────

    def _crawl_pages(self, session: requests.Session, path: str, max_pages: int) -> Iterator[tuple[str, str]]:
        """Yield (url, html) for every paginated page of the given category path."""
        page = 1
        seen_urls: set[str] = set()

        while True:
            params: dict = {"route": "product/category", "path": path}
            if page > 1:
                params["page"] = str(page)
            url = BASE_URL + "/index.php?" + "&".join(f"{k}={v}" for k, v in params.items())

            if url in seen_urls:
                break
            seen_urls.add(url)

            try:
                resp = session.get(url, timeout=30)
                resp.raise_for_status()
            except Exception as exc:
                break

            yield url, resp.text

            if max_pages and page >= max_pages:
                break

            # Check if next page exists in pagination
            soup = BeautifulSoup(resp.text, "html.parser")
            next_page = soup.select_one(f'a[href*="page={page + 1}"]')
            if not next_page:
                break
            page += 1

    def _extract_product_urls(self, soup: BeautifulSoup) -> Iterator[str]:
        """Yield canonical product URLs from a category listing page."""
        seen: set[str] = set()
        for a in soup.select('a[href*="route=product/product"][href*="product_id="]'):
            href = unescape(a.get("href", ""))
            # Skip quickview links
            if "quickview" in href:
                continue
            # Canonicalise: keep only product_id param
            m = re.search(r"product_id=(\d+)", href)
            if not m:
                continue
            canonical = f"{BASE_URL}/index.php?route=product/product&product_id={m.group(1)}"
            if canonical not in seen:
                seen.add(canonical)
                yield canonical

    # ──────────────────────────────────────────────────────────────────
    # Product parsing
    # ──────────────────────────────────────────────────────────────────

    def _parse_product(
        self,
        session: requests.Session,
        url: str,
        cat_obj: SealCategory,
        skip_images: bool,
    ) -> SealProduct:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # ── Title ──
        h1 = soup.find("h1")
        title = _clean_title(h1.get_text(" ", strip=True)) if h1 else ""
        if not title:
            og = soup.find("meta", property="og:title")
            title = _clean_title(og["content"]) if og else ""
        if not title:
            raise ValueError("No title found")

        # ── Description ──
        description = ""
        for tab_id in ("tab-description", "description", "product-tab-description"):
            el = soup.find(id=tab_id)
            if el:
                # Remove script/style
                for tag in el.find_all(["script", "style"]):
                    tag.decompose()
                description = _clean(el.get_text("\n", strip=True))
                # Strip repeated title at start
                if description.lower().startswith(title.lower()):
                    description = description[len(title):].lstrip()
                description = re.sub(r"^\s*>?\s*", "", description).strip()
                break

        # ── Attributes ──
        attributes: list[dict] = []
        attrs_text_parts: list[str] = []

        for row in soup.select("table.attribute tbody tr, table.attribute tr, .product-stats tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            name = _clean(cells[0].get_text(" ", strip=True))
            value = _clean(cells[1].get_text(" ", strip=True))
            if not name or not value:
                continue
            # Skip price/availability rows
            if any(skip in name.lower() for skip in SKIP_ATTR_NAMES):
                continue
            if any(skip in value.lower() for skip in SKIP_ATTR_NAMES):
                continue
            # Skip rows where the value looks like a price table (multiple newlines)
            if value.count("\n") > 2:
                continue
            # Clean up value whitespace
            value = re.sub(r"\s+", " ", value).strip()
            if len(value) > 200:
                continue
            attributes.append({"name": name, "value": value})
            attrs_text_parts.append(f"{name} {value}")

        # ── Image ──
        image_url = ""
        # Try og:image first
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            image_url = og_img["content"]
        # Fallback: first large product image
        if not image_url:
            for img in soup.select("#image, #main-image, .product-image img, .thumbnail img"):
                src = img.get("src", "") or img.get("data-src", "")
                if src:
                    image_url = src if src.startswith("http") else BASE_URL + src
                    break
        # Skip placeholders
        if any(f in image_url.lower() for f in SKIP_IMAGE_FRAGMENTS):
            image_url = ""

        # ── Save / Update ──
        product = SealProduct.objects.filter(source_url=url).first()
        if not product:
            product = SealProduct(source_url=url, slug=_unique_slug(title))

        product.name = title
        product.category = cat_obj
        product.description = description
        product.attributes = attributes
        product.attributes_text = _clean(" ".join(attrs_text_parts))
        product.image_url = image_url
        product.is_active = True

        if image_url and not skip_images:
            try:
                img_resp = session.get(image_url, timeout=30)
                if img_resp.ok:
                    ext = image_url.split("?")[0].rsplit(".", 1)[-1][:5]
                    fname = f"spbrezina_{product.slug[:40]}.{ext}"
                    product.image.save(fname, ContentFile(img_resp.content), save=False)
            except Exception:
                pass

        product.save()
        return product
