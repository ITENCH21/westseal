import re
import time
import urllib.parse
from typing import Iterable

import requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from html import unescape

from apps.core.models import SealCategory, SealProduct


BASE_URL = "https://www.mkt-rti.ru"
CATALOG_URL = f"{BASE_URL}/catalog/"


def _clean_url(url: str) -> str:
    if not url:
        return ""
    url = url.split("#")[0]
    return url


def _full_url(href: str) -> str:
    if not href:
        return ""
    return urllib.parse.urljoin(BASE_URL, href)


def _is_product_url(path: str) -> bool:
    # /catalog/<cat>/<sub>/<id>/
    return bool(re.match(r"^/catalog/[^/]+/(?:[^/]+/)?\d+/?$", path))


def _is_category_url(path: str) -> bool:
    return bool(re.match(r"^/catalog/[^/]+/?$", path))


def _is_subcategory_url(path: str) -> bool:
    return bool(re.match(r"^/catalog/[^/]+/[^/]+/?$", path)) and not _is_product_url(path)


def _unique_slug(model, base: str) -> str:
    base_slug = slugify(base) or "item"
    slug = base_slug
    idx = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{idx}"
        idx += 1
    return slug


def _normalize_text(value: str, *, keep_newlines: bool = False) -> str:
    if not value:
        return ""
    text = unescape(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    # sometimes descriptions end up with literal "\n"
    text = text.replace("\\n", "\n")
    # normalize dimension separators only when used between numbers
    text = re.sub(r"(?<=\d)\s*[×xХх]\s*(?=\d)", "x", text)
    # fix duplicated punctuation from messy sources: 12,,7 -> 12,7
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r"\.\s*\.+", ".", text)
    text = re.sub(r"\s*;\s*;", ";", text)
    if keep_newlines:
        text = "\n".join(re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.split("\n"))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text
    text = text.replace("\n", " ")
    text = re.sub(r"[ \t\f\v]+", " ", text).strip()
    return text


class Command(BaseCommand):
    help = "Import seal catalog from mkt-rti.ru into local database."

    def add_arguments(self, parser):
        parser.add_argument("--category", help="Parse only one top category slug (e.g. uplotnenija_porshnja)")
        parser.add_argument("--limit", type=int, default=0, help="Limit total products to import")
        parser.add_argument("--max-pages", type=int, default=0, help="Limit pages per category (0 = no limit)")
        parser.add_argument("--no-images", action="store_true", help="Skip downloading images")
        parser.add_argument("--sleep", type=float, default=0.4, help="Delay between requests (seconds)")
        parser.add_argument("--log-file", default="data/import_mkt_rti.log", help="Log file path")

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
                "User-Agent": "Mozilla/5.0 (compatible; EURO-SEAL bot)",
                "Accept-Language": "ru,en;q=0.8",
            }
        )

        log("Fetching catalog index...")
        html = session.get(CATALOG_URL, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")
        category_links = self._extract_category_links(soup)
        log(f"Found categories: {len(category_links)}")

        if options["category"]:
            category_links = [c for c in category_links if c["slug"] == options["category"]]
            if not category_links:
                self.stdout.write(self.style.WARNING("Category slug not found on index."))
                return

        categories_map = {}
        for cat in category_links:
            obj, _ = SealCategory.objects.get_or_create(
                slug=cat["slug"],
                defaults={
                    "name": cat["name"],
                    "source_url": cat["url"],
                },
            )
            obj.name = cat["name"]
            obj.source_url = cat["url"]
            obj.is_active = True
            obj.save(update_fields=["name", "source_url", "is_active"])
            categories_map[cat["slug"]] = obj

        total_imported = 0
        for cat in category_links:
            if options["limit"] and total_imported >= options["limit"]:
                break
            log(f"Parsing category: {cat['name']} ({cat['url']})")
            cat_obj = categories_map.get(cat["slug"])
            subcategories = {}

            seen = set()

            def import_url(url: str, idx: int | None = None, total: int | None = None):
                nonlocal total_imported
                if url in seen:
                    return
                seen.add(url)
                if options["limit"] and total_imported >= options["limit"]:
                    return
                try:
                    product = self._parse_product(session, url, cat_obj, subcategories, options["no_images"])
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

            # import products from category pages and discover subcategories as we crawl
            for page_url, page_html in self._crawl_pages(session, cat["url"], options["max_pages"]):
                log(f"  Category page: {page_url}")
                page_soup = BeautifulSoup(page_html, "html.parser")
                for sub in self._extract_subcategory_links(page_soup, cat["slug"]):
                    if sub["slug"] in subcategories:
                        continue
                    slug = f"{cat['slug']}-{sub['code']}" if sub["code"] else f"{cat['slug']}-sub"
                    slug = slugify(slug)
                    obj, _ = SealCategory.objects.get_or_create(
                        slug=slug,
                        defaults={
                            "name": sub["name"],
                            "code": sub["code"],
                            "parent": cat_obj,
                            "source_url": sub["url"],
                        },
                    )
                    obj.name = sub["name"] or obj.name
                    obj.code = sub["code"]
                    obj.parent = cat_obj
                    obj.source_url = sub["url"]
                    obj.is_active = True
                    obj.save(update_fields=["name", "code", "parent", "source_url", "is_active"])
                    subcategories[sub["slug"]] = obj
                for url in self._extract_product_links(page_soup, cat["slug"]):
                    import_url(url)
                    if options["limit"] and total_imported >= options["limit"]:
                        break
                if options["limit"] and total_imported >= options["limit"]:
                    break

            # then import products from each subcategory page (with pagination)
            for sub in subcategories.values():
                if options["limit"] and total_imported >= options["limit"]:
                    break
                page_idx = 0
                for page_url, sub_html in self._crawl_pages(session, sub.source_url, options["max_pages"]):
                    page_idx += 1
                    log(f"  Subcategory {sub.code or sub.name}: page {page_idx} {page_url}")
                    sub_soup = BeautifulSoup(sub_html, "html.parser")
                    collected = list(self._extract_product_links(sub_soup, cat["slug"]))
                    total_links = len(collected)
                    for idx, url in enumerate(collected, start=1):
                        if options["limit"] and total_imported >= options["limit"]:
                            break
                        import_url(url, idx, total_links)
                    if options["limit"] and total_imported >= options["limit"]:
                        break

        log(f"Done. Imported {total_imported} products.")
        log_fp.close()

    def _extract_category_links(self, soup: BeautifulSoup) -> list[dict]:
        items = {}
        for a in soup.select('a[href*="/catalog/"]'):
            raw = _clean_url(a.get("href", ""))
            path = urllib.parse.urlparse(raw).path or raw
            if path == "/catalog/":
                continue
            if not _is_category_url(path):
                continue
            name = a.get_text(strip=True)
            if not name:
                continue
            slug = path.strip("/").split("/")[1]
            items[slug] = {
                "name": name,
                "slug": slug,
                "url": _full_url(path),
            }
        return list(items.values())

    def _extract_subcategory_links(self, soup: BeautifulSoup, cat_slug: str) -> list[dict]:
        items = {}
        for a in soup.select('a[href*="/catalog/"]'):
            raw = _clean_url(a.get("href", ""))
            path = urllib.parse.urlparse(raw).path or raw
            if not _is_subcategory_url(path):
                continue
            parts = path.strip("/").split("/")
            if len(parts) < 3 or parts[1] != cat_slug:
                continue
            sub_slug = parts[2]
            name = a.get_text(strip=True) or sub_slug.upper()
            items[sub_slug] = {
                "name": name,
                "slug": sub_slug,
                "code": sub_slug.upper(),
                "url": _full_url(path),
            }
        return list(items.values())

    def _extract_product_links(self, soup: BeautifulSoup, cat_slug: str) -> Iterable[str]:
        for a in soup.select('a[href*="/catalog/"]'):
            raw = _clean_url(a.get("href", ""))
            path = urllib.parse.urlparse(raw).path or raw
            if not _is_product_url(path):
                continue
            parts = path.strip("/").split("/")
            if len(parts) < 3 or parts[1] != cat_slug:
                continue
            yield _full_url(path)

    def _crawl_pages(self, session: requests.Session, start_url: str, max_pages: int) -> Iterable[tuple[str, str]]:
        base = start_url.split("?")[0]
        queue = [start_url]
        seen = set()
        while queue:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            html = session.get(url, timeout=30).text
            yield url, html
            if max_pages and len(seen) >= max_pages:
                break
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select('a[href*="PAGEN_"]'):
                href = a.get("href", "")
                if not href:
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

    def _parse_product(self, session: requests.Session, url: str, cat_obj: SealCategory, sub_map: dict, skip_images: bool) -> SealProduct:
        html = session.get(url, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")
        title_el = soup.find("h1")
        if title_el:
            title = _normalize_text(title_el.get_text(" ", strip=True))
        else:
            meta_title = soup.find("meta", property="og:title")
            title = _normalize_text(meta_title.get("content", "") if meta_title else "")
        if not title:
            raise ValueError("Missing product title")
        # Пропускаем обзорные страницы каталога (название "Каталог *")
        if title.lower().startswith("каталог"):
            raise ValueError(f"Skipping catalog overview page: {title!r}")
        desc_el = soup.select_one("div#descr")
        raw_desc = desc_el.get_text("\n", strip=True) if desc_el else ""
        description = _normalize_text(raw_desc, keep_newlines=True)
        # Strip leading section header "Описание" that mkt-rti embeds as first line
        description = re.sub(r"^\s*Описание\s*\n+", "", description, flags=re.IGNORECASE).strip()

        attributes = []
        attrs_text = []
        for row in soup.select("table.props_list tr"):
            name = row.select_one(".char_name")
            value = row.select_one(".char_value")
            if not name or not value:
                continue
            name_text = _normalize_text(name.get_text(" ", strip=True))
            value_text = _normalize_text(value.get_text(" ", strip=True))
            attributes.append({"name": name_text, "value": value_text})
            attrs_text.append(f"{name_text} {value_text}")

        og = soup.find("meta", property="og:image")
        image_url = og["content"] if og else ""

        product = SealProduct.objects.filter(source_url=url).first()
        if not product:
            slug = _unique_slug(SealProduct, title)
            product = SealProduct(
                source_url=url,
                slug=slug,
            )

        product.name = title
        product.category = cat_obj
        product.subcategory = self._infer_subcategory(url, sub_map)
        product.image_url = image_url
        product.description = description
        product.attributes = attributes
        product.attributes_text = _normalize_text(" ".join(attrs_text))
        product.is_active = True

        if image_url and not skip_images:
            try:
                img_resp = session.get(image_url, timeout=30)
                if img_resp.ok:
                    filename = image_url.split("/")[-1]
                    product.image.save(filename, ContentFile(img_resp.content), save=False)
            except Exception:
                pass

        product.save()
        return product

    def _infer_subcategory(self, url: str, sub_map: dict) -> SealCategory | None:
        path = urllib.parse.urlparse(url).path.strip("/").split("/")
        if len(path) >= 4:
            code = path[2]
            return sub_map.get(code)
        return None
