"""
Import ALL seal products from https://www.krpms.ru/catalog/uplotneniya/

COMPLETE category coverage:
  - Грязесъемники (KRPMS, Aston Seals, Kastas, Пыльники)
  - Уплотнения штока (KRPMS, Aston Seals, Kastas)
  - Уплотнения поршня (KRPMS, Aston Seals, Kastas)
  - Симметричные уплотнения (KRPMS, Aston Seals, Kastas)
  - Направляющие кольца (KRPMS, Aston Seals, Kastas)
  - Статические уплотнения (KRPMS, Aston Seals, Kastas)
  - Опорные кольца (Центрирующие)
  - Пневматические уплотнения (Aston Seals, Kastas)
  - Уплотнительные кольца (Комплекты, МБС, Разрезные)
  - Роторные уплотнения
  - Комплекты уплотнений гидроцилиндров
  - Уплотнения большого диаметра
  - Уплотнения для горной промышленности
  - О-кольца круглого сечения
  - Воротниковые манжеты
  - Резиновые манжеты
  - Силиконовые кольца
  - Манжеты уплотнительные (для гидроцилиндров)
  - Шевронные манжеты

Usage:
    python manage.py import_krpms_full
    python manage.py import_krpms_full --section gryazesemnik-krpms --limit 5 --no-images
    python manage.py import_krpms_full --sleep 0.4 --log-file data/import_krpms2.log
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
SLUG_PREFIX = "krpms-"

# Logo patterns to skip
LOGO_PATTERNS = ["local/templates/", "/img/krpms", "krpms.webp"]


def _is_logo(url: str) -> bool:
    return any(p in url for p in LOGO_PATTERNS)


# ---------------------------------------------------------------------------
# Complete section map:
#   (url_suffix,  section_key,  db_cat_slug,  db_cat_name,  brand_tag)
#
#   db_cat_slug   — slug of the SealCategory to assign products to
#   db_cat_name   — used only if category doesn't exist yet (auto-create)
#   brand_tag     — stored as product attribute "Производитель"
# ---------------------------------------------------------------------------
CATALOG_SECTIONS = [
    # ── Грязесъемники ──────────────────────────────────────────────────
    ("/catalog/uplotneniya/gryazesemniki/gryazesemnik-krpms/",
     "gryazesemnik-krpms", "grjazesemniki", "Грязесъемники", "KRPMS"),
    ("/catalog/uplotneniya/gryazesemniki/gryazesemniki-aston-seals/",
     "gryazesemniki-aston-seals", "grjazesemniki", "Грязесъемники", "Aston Seals"),
    ("/catalog/uplotneniya/gryazesemniki/gryazesemniki-kastas/",
     "gryazesemniki-kastas", "grjazesemniki", "Грязесъемники", "Kastas"),
    ("/catalog/uplotneniya/gryazesemniki/pylniki/",
     "pylniki", "grjazesemniki", "Грязесъемники", ""),

    # ── Уплотнения штока ───────────────────────────────────────────────
    ("/catalog/uplotneniya/uplotneniya-shtoka/uplotneniya-shtoka-krpms/",
     "uplotneniya-shtoka-krpms", "uplotnenija_shtoka", "Уплотнения штока", "KRPMS"),
    ("/catalog/uplotneniya/uplotneniya-shtoka/uplotneniya-shtoka-aston-seals/",
     "uplotneniya-shtoka-aston-seals", "uplotnenija_shtoka", "Уплотнения штока", "Aston Seals"),
    ("/catalog/uplotneniya/uplotneniya-shtoka/uplotneniya-shtoka-kastas/",
     "uplotneniya-shtoka-kastas", "uplotnenija_shtoka", "Уплотнения штока", "Kastas"),

    # ── Уплотнения поршня ──────────────────────────────────────────────
    ("/catalog/uplotneniya/uplotneniya-porshnya/uplotneniya-porshnya-krpms/",
     "uplotneniya-porshnya-krpms", "uplotnenija_porshnja", "Уплотнения поршня", "KRPMS"),
    ("/catalog/uplotneniya/uplotneniya-porshnya/uplotneniya-porshnya-aston-seals/",
     "uplotneniya-porshnya-aston-seals", "uplotnenija_porshnja", "Уплотнения поршня", "Aston Seals"),
    ("/catalog/uplotneniya/uplotneniya-porshnya/uplotneniya-porshnya-kastas/",
     "uplotneniya-porshnya-kastas", "uplotnenija_porshnja", "Уплотнения поршня", "Kastas"),

    # ── Симметричные уплотнения → Манжеты гидравлические ──────────────
    ("/catalog/uplotneniya/simmetrichnye-uplotneniya/simmetrichnye-uplotneniya-krpms/",
     "simmetrichnye-krpms", "manzhety_gidravlicheskie", "Манжеты гидравлические универсальные", "KRPMS"),
    ("/catalog/uplotneniya/simmetrichnye-uplotneniya/simmetrichnye-uplotneniya-aston-seals/",
     "simmetrichnye-aston", "manzhety_gidravlicheskie", "Манжеты гидравлические универсальные", "Aston Seals"),
    ("/catalog/uplotneniya/simmetrichnye-uplotneniya/simmetrichnye-uplotneniya-kastas/",
     "simmetrichnye-kastas", "manzhety_gidravlicheskie", "Манжеты гидравлические универсальные", "Kastas"),

    # ── Направляющие / опорные кольца → Направляющие гидроцилиндров ──
    ("/catalog/uplotneniya/napravlyayushhie-kolca-dlya-gidrocilindrov/napravlyayuschie-koltsa-krpms/",
     "napravlyayushchie-krpms", "napravljajuwie_gidrocilindrov", "Направляющие гидроцилиндров", "KRPMS"),
    ("/catalog/uplotneniya/napravlyayushhie-kolca-dlya-gidrocilindrov/napravlyayuschie-koltsa-aston-seals/",
     "napravlyayushchie-aston", "napravljajuwie_gidrocilindrov", "Направляющие гидроцилиндров", "Aston Seals"),
    ("/catalog/uplotneniya/napravlyayushhie-kolca-dlya-gidrocilindrov/napravlyayuschie-koltsa-kastas/",
     "napravlyayushchie-kastas", "napravljajuwie_gidrocilindrov", "Направляющие гидроцилиндров", "Kastas"),
    ("/catalog/uplotneniya/opornye-koltsa/czentriruyushhie/",
     "opornye-centriruyushchie", "napravljajuwie_gidrocilindrov", "Направляющие гидроцилиндров", ""),

    # ── Статические уплотнения → Кольца уплотнительные ───────────────
    ("/catalog/uplotneniya/staticheskie-uplotneniya/staticheskie-uplotneniya-krpms/",
     "staticheskie-krpms", "kolca_uplatnitelnye", "Кольца уплотнительные", "KRPMS"),
    ("/catalog/uplotneniya/staticheskie-uplotneniya/staticheskie-uplotneniya-aston-seals/",
     "staticheskie-aston", "kolca_uplatnitelnye", "Кольца уплотнительные", "Aston Seals"),
    ("/catalog/uplotneniya/staticheskie-uplotneniya/staticheskie-uplotneniya-kastas/",
     "staticheskie-kastas", "kolca_uplatnitelnye", "Кольца уплотнительные", "Kastas"),

    # ── Пневматические уплотнения ─────────────────────────────────────
    ("/catalog/uplotneniya/pnevmaticheskie-uplotneniya-shtoka/pnevmaticheskie-uplotneniya-aston-seals/",
     "pnevma-aston", "pnevmaticheskoe_uplotnenija", "Пневматические уплотнения", "Aston Seals"),
    ("/catalog/uplotneniya/pnevmaticheskie-uplotneniya-shtoka/pnevmaticheskie-uplotneniya-shtoka-kastas/",
     "pnevma-kastas", "pnevmaticheskoe_uplotnenija", "Пневматические уплотнения", "Kastas"),

    # ── О-кольца и уплотнительные кольца ─────────────────────────────
    ("/catalog/uplotneniya/uplotnitelnye-kolcza/komplekty/",
     "koltca-komplekty", "kolca_uplatnitelnye", "Кольца уплотнительные", ""),
    ("/catalog/uplotneniya/uplotnitelnye-kolcza/maslobenzostojkie/",
     "koltca-mbs", "kolca_uplatnitelnye", "Кольца уплотнительные", ""),
    ("/catalog/uplotneniya/uplotnitelnye-kolcza/razreznye/",
     "koltca-razreznye", "kolca_uplatnitelnye", "Кольца уплотнительные", ""),
    ("/catalog/uplotneniya/kruglogo-secheniya/",
     "o-koltca", "kolca_uplatnitelnye", "Кольца уплотнительные", ""),

    # ── Роторные уплотнения → Специальные уплотнения ──────────────────
    ("/catalog/uplotneniya/rotornye-uplotneniya/",
     "rotornye", "specialnye_uplotnenija", "Специальные уплотнения", ""),

    # ── Комплекты / большой диаметр → Специальные уплотнения ─────────
    ("/catalog/uplotneniya/komplekty-uplotneniy/",
     "komplekty-uplotneniy", "specialnye_uplotnenija", "Специальные уплотнения", ""),
    ("/catalog/uplotneniya/uplotneniya-bolshogo-diametra/",
     "bolshoi-diametr", "specialnye_uplotnenija", "Специальные уплотнения", ""),

    # ── Уплотнения для горной промышленности → Специальные ────────────
    ("/catalog/uplotneniya/uplotneniya-dlya-gornoy-promyshlennosti/",
     "gornaya", "specialnye_uplotnenija", "Специальные уплотнения", ""),

    # ── Манжеты для гидроцилиндров → Манжеты гидравлические ──────────
    ("/catalog/uplotneniya/manzhety-uplotnitelnye/dlya-gidroczilindrov/",
     "manzhety-gidro", "manzhety_gidravlicheskie", "Манжеты гидравлические универсальные", ""),

    # ── Воротниковые манжеты → Манжеты гидравлические ────────────────
    ("/catalog/uplotneniya/vorotnikovye/",
     "vorotnikovye", "manzhety_gidravlicheskie", "Манжеты гидравлические универсальные", ""),

    # ── Резиновые манжеты → Манжеты гидравлические ───────────────────
    ("/catalog/uplotneniya/rezinovye/",
     "rezinovye", "manzhety_gidravlicheskie", "Манжеты гидравлические универсальные", ""),

    # ── Силиконовые кольца → Кольца уплотнительные ───────────────────
    ("/catalog/uplotneniya/silikonovye/",
     "silikonovye", "kolca_uplatnitelnye", "Кольца уплотнительные", ""),

    # ── Шевронные манжеты ─────────────────────────────────────────────
    ("/catalog/uplotneniya/manzheta-shevronnaya/",
     "shevronnye", "manzheti_shevronnie", "Шевронные уплотнения и манжеты", ""),
]


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _full_url(href: str) -> str:
    if not href:
        return ""
    return urllib.parse.urljoin(BASE_URL, href)


def _norm_path(href: str) -> str:
    raw = href.split("#")[0]
    return urllib.parse.urlparse(raw).path or raw


def _is_product_url(path: str) -> bool:
    return path.endswith(".html") and "/catalog/uplotneniya/" in path


def _normalize_text(value: str, *, keep_newlines: bool = False) -> str:
    if not value:
        return ""
    text = unescape(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = text.replace("\\n", "\n")
    text = re.sub(r"(?<=\d)\s*[×xХх]\s*(?=\d)", "x", text)
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
# Management Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Full import from krpms.ru — all seal categories with hardcoded section list."

    def add_arguments(self, parser):
        parser.add_argument(
            "--section",
            help="Import only one section by its section_key (e.g. gryazesemnik-krpms)",
        )
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Max total products (0 = no limit)",
        )
        parser.add_argument(
            "--no-images", action="store_true",
            help="Skip downloading product images",
        )
        parser.add_argument(
            "--sleep", type=float, default=0.4,
            help="Delay between requests (seconds)",
        )
        parser.add_argument(
            "--log-file", default="data/import_krpms2.log",
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ru,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        sections = CATALOG_SECTIONS
        if options["section"]:
            sections = [s for s in CATALOG_SECTIONS if s[1] == options["section"]]
            if not sections:
                log(f"Section '{options['section']}' not found. Keys: " +
                    ", ".join(s[1] for s in CATALOG_SECTIONS))
                return

        # Pre-load / auto-create DB categories
        cat_cache: dict[str, SealCategory] = {}
        for url_suf, sec_key, db_slug, db_name, brand in sections:
            if db_slug not in cat_cache:
                cat = SealCategory.objects.filter(slug=db_slug).first()
                if not cat:
                    cat = SealCategory.objects.create(
                        slug=db_slug,
                        name=db_name,
                        parent=None,
                        is_active=True,
                    )
                    log(f"  Created new category: {db_slug} ({db_name})")
                else:
                    if not cat.is_active:
                        cat.is_active = True
                        cat.save(update_fields=["is_active"])
                cat_cache[db_slug] = cat

        total_imported = 0
        total_updated = 0

        for url_suf, sec_key, db_slug, db_name, brand in sections:
            if options["limit"] and total_imported >= options["limit"]:
                break

            cat_obj = cat_cache[db_slug]
            section_url = BASE_URL + url_suf
            log(f"\n{'═'*70}")
            log(f"Section: {sec_key}  →  {cat_obj.name} [{db_slug}]")
            if brand:
                log(f"  Brand: {brand}")
            log(f"  URL:  {section_url}")

            # Collect all product URLs from all pages
            all_product_urls: list[str] = []
            seen_pages: set[str] = set()
            page_queue = [section_url]

            while page_queue:
                page_url = page_queue.pop(0)
                if page_url in seen_pages:
                    continue
                seen_pages.add(page_url)

                try:
                    resp = session.get(page_url, timeout=30)
                    if resp.status_code == 404:
                        log(f"  404 — skipping section")
                        break
                    page_html = resp.text
                except Exception as exc:
                    log(f"  ERROR fetching page: {exc}")
                    break

                soup = BeautifulSoup(page_html, "html.parser")

                # Collect product links
                for a in soup.select('a[href]'):
                    href = a.get("href", "")
                    path = _norm_path(href)
                    if _is_product_url(path):
                        full = _full_url(path)
                        if full not in all_product_urls:
                            all_product_urls.append(full)

                # Discover next PAGEN_ pages
                base_path = urllib.parse.urlparse(section_url).path
                for a in soup.select('a[href*="PAGEN_"]'):
                    href = a.get("href", "")
                    if not href:
                        continue
                    if href.startswith("?"):
                        full_pg = BASE_URL + base_path + href
                    elif href.startswith("/"):
                        full_pg = BASE_URL + href
                    else:
                        full_pg = BASE_URL + "/" + href.lstrip("/")
                    parsed_pg = urllib.parse.urlparse(full_pg)
                    # Only accept pages under the same path
                    if parsed_pg.path != base_path:
                        continue
                    q = urllib.parse.parse_qs(parsed_pg.query)
                    page_params = {k: v[-1] for k, v in q.items()
                                   if k.startswith("PAGEN_")}
                    if not page_params:
                        continue
                    canonical = BASE_URL + base_path + "?" + urllib.parse.urlencode(page_params)
                    if canonical not in seen_pages:
                        page_queue.append(canonical)

                time.sleep(options["sleep"] * 0.5)

            log(f"  Found {len(all_product_urls)} product URLs across {len(seen_pages)} page(s)")
            if not all_product_urls:
                continue

            for idx, url in enumerate(all_product_urls, start=1):
                if options["limit"] and total_imported >= options["limit"]:
                    break
                try:
                    product, created = self._parse_and_save(
                        session, url, cat_obj, brand, options["no_images"]
                    )
                except Exception as exc:
                    log(f"  [{idx}/{len(all_product_urls)}] FAIL: {url}  ({exc})")
                    continue

                if created:
                    total_imported += 1
                else:
                    total_updated += 1

                processed = total_imported + total_updated
                elapsed = max(1.0, time.time() - start_ts)
                rate = processed / elapsed
                remaining = len(all_product_urls) - idx
                eta_min = int(remaining / max(rate, 0.1)) // 60
                action = "NEW" if created else "UPD"
                log(f"  [{idx}/{len(all_product_urls)}] {action} new={total_imported} "
                    f"upd={total_updated} eta~{eta_min}m: {product.name[:60]}")
                time.sleep(options["sleep"])

        elapsed_total = int(time.time() - start_ts)
        log(f"\n{'═'*70}")
        log(f"Done. New: {total_imported}  Updated: {total_updated}  "
            f"Time: {elapsed_total//60}m {elapsed_total%60}s")
        log_fp.close()

    # -----------------------------------------------------------------------
    # Product parser
    # -----------------------------------------------------------------------

    def _parse_and_save(
        self,
        session: requests.Session,
        url: str,
        cat_obj: SealCategory,
        brand: str,
        skip_images: bool,
    ) -> tuple[SealProduct, bool]:
        html = session.get(url, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")

        # ── Title ────────────────────────────────────────────────────────
        h1 = soup.find("h1")
        title = _normalize_text(h1.get_text(" ", strip=True)) if h1 else ""
        if not title:
            og = soup.find("meta", property="og:title")
            title = _normalize_text(og.get("content", "")) if og else ""
        if not title:
            raise ValueError("No title found")

        # ── Attributes / general properties ──────────────────────────────
        attributes: list[dict] = []
        attrs_text_parts: list[str] = []

        # Brand as first attribute (if known)
        if brand:
            attributes.append({"name": "Производитель", "value": brand})
            attrs_text_parts.append(f"Производитель {brand}")

        # Method 1: mkt-rti style table.props_list (char_name / char_value)
        for row in soup.select("table.props_list tr"):
            name_el = row.select_one(".char_name")
            value_el = row.select_one(".char_value")
            if name_el and value_el:
                n = _normalize_text(name_el.get_text(" ", strip=True))
                v = _normalize_text(value_el.get_text(" ", strip=True))
                if n and v:
                    attributes.append({"name": n, "value": v})
                    attrs_text_parts.append(f"{n} {v}")

        # Method 2: krpms-specific "production-properties" divs
        #   <h2>Общие свойства</h2>
        #   <div class="production-properties">
        #     <div class="production-properties-title">Давление:</div>
        #     <div class="production-properties-description">-</div>
        #     <div class="production-properties-title">Код уплотнения:</div>
        #     <div class="production-properties-description">WR01</div>
        #   </div>
        if len(attributes) == (1 if brand else 0):
            prop_container = soup.find("div", class_="production-properties")
            if prop_container:
                titles = prop_container.find_all("div", class_="production-properties-title")
                descs = prop_container.find_all("div", class_="production-properties-description")
                for title_el, desc_el in zip(titles, descs):
                    n = _normalize_text(title_el.get_text(" ", strip=True)).rstrip(":")
                    v = _normalize_text(desc_el.get_text(" ", strip=True))
                    if n:
                        if n.lower() == "производитель" and brand:
                            continue
                        if v and v not in ("-", "—"):
                            attributes.append({"name": n, "value": v})
                            attrs_text_parts.append(f"{n} {v}")
                        elif not v or v in ("-", "—"):
                            # Include even empty values for completeness
                            attributes.append({"name": n, "value": ""})

        # Method 2b: generic heading → sibling search
        if len(attributes) == (1 if brand else 0):
            for heading in soup.find_all(["h2", "h3"]):
                if not re.search(r"свойств|характеристик|параметр", heading.get_text(), re.IGNORECASE):
                    continue
                container = heading.find_next_sibling()
                if container is None:
                    continue
                # Try <table> inside container
                tbl = container if container.name == "table" else container.find("table")
                if tbl:
                    for row in tbl.find_all("tr"):
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            n = _normalize_text(cells[0].get_text(" ", strip=True))
                            v = _normalize_text(cells[1].get_text(" ", strip=True))
                            if n and v and v not in ("-", "—"):
                                if n.lower() == "производитель" and brand:
                                    continue
                                attributes.append({"name": n, "value": v})
                                attrs_text_parts.append(f"{n} {v}")
                    if len(attributes) > (1 if brand else 0):
                        break
                # Try <ul>/<li> with colon separator
                for li in container.find_all("li"):
                    text = li.get_text(" ", strip=True)
                    if ":" in text:
                        n, _, v = text.partition(":")
                        n = _normalize_text(n)
                        v = _normalize_text(v)
                        if n and v:
                            attributes.append({"name": n, "value": v})
                            attrs_text_parts.append(f"{n} {v}")
                if len(attributes) > (1 if brand else 0):
                    break

        # Method 3: generic dl / dt+dd
        if len(attributes) == (1 if brand else 0):
            for dl in soup.find_all("dl"):
                dts = dl.find_all("dt")
                dds = dl.find_all("dd")
                for dt, dd in zip(dts, dds):
                    n = _normalize_text(dt.get_text(" ", strip=True))
                    v = _normalize_text(dd.get_text(" ", strip=True))
                    if n and v:
                        attributes.append({"name": n, "value": v})
                        attrs_text_parts.append(f"{n} {v}")
                if len(attributes) > (1 if brand else 0):
                    break

        # ── Description ───────────────────────────────────────────────────
        description = ""
        for heading in soup.find_all(["h2", "h3"]):
            if re.search(r"описание|характеристик", heading.get_text(), re.IGNORECASE):
                parts = []
                for sib in heading.find_next_siblings():
                    if sib.name in ("h1", "h2", "h3"):
                        break
                    t = sib.get_text("\n", strip=True)
                    if t:
                        parts.append(t)
                description = _normalize_text("\n".join(parts), keep_newlines=True)
                if description:
                    break

        # ── Image ─────────────────────────────────────────────────────────
        # krpms.ru: real product images (when they exist) are in /upload/iblock/
        # The logo at local/templates/ is NOT a product image — skip it
        image_url = ""
        for img in soup.find_all("img", src=True):
            src = img.get("src", "")
            if "/upload/iblock/" in src and not _is_logo(src):
                image_url = _full_url(src)
                break
        if not image_url and not skip_images:
            # Try og:image but only if it's a real product image
            og_img = soup.find("meta", property="og:image")
            if og_img:
                cand = og_img.get("content", "")
                if cand and not _is_logo(cand):
                    image_url = cand

        # ── Save / Update ─────────────────────────────────────────────────
        existing = SealProduct.objects.filter(source_url=url).first()
        created = existing is None

        if created:
            slug = _unique_slug(SealProduct, title)
            product = SealProduct(source_url=url, slug=slug)
        else:
            product = existing

        product.name = title
        product.category = cat_obj
        product.subcategory = None
        product.image_url = ""          # never store external logo
        product.description = description
        product.attributes = attributes
        product.attributes_text = _normalize_text(" ".join(attrs_text_parts))
        product.is_active = True

        if image_url and not skip_images:
            try:
                img_resp = session.get(image_url, timeout=30)
                if img_resp.ok and len(img_resp.content) > 2000:  # skip tiny/empty
                    filename = image_url.split("/")[-1].split("?")[0] or "product.jpg"
                    product.image.save(filename, ContentFile(img_resp.content), save=False)
            except Exception:
                pass

        product.save()
        return product, created
