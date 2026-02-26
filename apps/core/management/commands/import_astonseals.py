"""
Import seal profile cards from https://astonseals.com/en/products/

Sections imported:
  /en/products/piston-seals/                  → uplotnenija_porshnja
  /en/products/rod-seals/                     → uplotnenija_shtoka
  /en/products/wipers/                        → grjazesemniki
  /en/products/guide-rings/                   → napravljajuwie_gidrocilindrov
  /en/products/rod-piston-seals/              → uplotnenija_porshnja
  /en/products/others/                        → specialnye_uplotnenija
  /en/products/elements-for-rod-pneumatic/    → pnevmaticheskoe_uplotnenija
  /en/products/elements-for-piston-pneumatic/ → pnevmaticheskoe_uplotnenija

Products live DIRECTLY on the listing page (no individual product URL).
source_url = category_page_url + "#" + profile_code

Usage:
    python manage.py import_astonseals
    python manage.py import_astonseals --section piston-seals
    python manage.py import_astonseals --no-images
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

BASE_URL = "https://astonseals.com"
SLUG_PREFIX = "aston-"

SECTIONS = [
    ("piston-seals",                   "/en/products/piston-seals/",                  "uplotnenija_porshnja"),
    ("rod-seals",                      "/en/products/rod-seals/",                     "uplotnenija_shtoka"),
    ("wipers",                         "/en/products/wipers/",                        "grjazesemniki"),
    ("guide-rings",                    "/en/products/guide-rings/",                   "napravljajuwie_gidrocilindrov"),
    ("rod-piston-seals",               "/en/products/rod-piston-seals/",              "uplotnenija_porshnja"),
    ("others",                         "/en/products/others/",                        "specialnye_uplotnenija"),
    ("pneumatic-rod",                  "/en/products/elements-for-rod-pneumatic/",    "pnevmaticheskoe_uplotnenija"),
    ("pneumatic-piston",               "/en/products/elements-for-piston-pneumatic/", "pnevmaticheskoe_uplotnenija"),
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
    help = "Import seal profile cards from astonseals.com (products on listing page)"

    def add_arguments(self, parser):
        parser.add_argument("--section", help="Only import one section key (e.g. piston-seals)")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--no-images", action="store_true")
        parser.add_argument("--sleep", type=float, default=0.0)
        parser.add_argument("--log-file", default="data/import_aston.log")

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
            cards = self._extract_cards(soup, page_url)
            log(f"  Found {len(cards)} profile cards")

            for idx, card in enumerate(cards, 1):
                if options["limit"] and total_imported >= options["limit"]:
                    break
                try:
                    product = self._save_card(session, card, cat, options["no_images"])
                except Exception as exc:
                    log(f"  FAIL [{idx}] {card.get('code','?')}: {exc}")
                    continue

                total_imported += 1
                log(f"  [{idx}/{len(cards)}] {product.name}  (total={total_imported})")
                if options["sleep"]:
                    time.sleep(options["sleep"])

        log(f"\nDone. Imported {total_imported} products from astonseals.com")
        log_fp.close()

    # ------------------------------------------------------------------ #

    def _extract_cards(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        """
        On astonseals.com listing pages each profile is a distinct block that
        contains an <img>, a heading / code link, description text and a bullet
        list with Pressure/Speed/Temperature/Material lines.

        We look for any container that holds BOTH an <img src="*.gif"> and a
        <li> with "Pressure" or "Speed" text.
        """
        cards = []
        seen_codes: set[str] = set()

        # Strategy 1: look for typical card wrappers
        wrappers = soup.find_all(class_=re.compile(
            r"(product.item|seal.item|catalog.item|card|entry|row.seal)", re.I
        ))

        # Strategy 2: fall back to any div/article containing a .gif img + bullet list
        if not wrappers:
            wrappers = []
            for img in soup.find_all("img", src=re.compile(r"\.gif", re.I)):
                parent = img.parent
                for _ in range(8):
                    if parent is None:
                        break
                    text = parent.get_text(" ")
                    if re.search(r"pressure|speed|temperature", text, re.I):
                        wrappers.append(parent)
                        break
                    parent = parent.parent

        for block in wrappers:
            card = self._parse_card_block(block, page_url)
            if card and card["code"] not in seen_codes:
                seen_codes.add(card["code"])
                cards.append(card)

        return cards

    def _parse_card_block(self, block: BeautifulSoup, page_url: str) -> dict | None:
        # Code — look for a prominent link or heading
        code = ""
        for tag in block.find_all(["h2", "h3", "h4", "strong", "a"]):
            text = _norm(tag.get_text(" ", strip=True))
            if re.match(r"^[A-Z]{1,6}[A-Z0-9+\-]{0,8}$", text):
                code = text
                break
        if not code:
            return None

        # Image
        img_tag = block.find("img", src=True)
        image_url = ""
        if img_tag:
            src = img_tag.get("src", "")
            image_url = src if src.startswith("http") else urllib.parse.urljoin(BASE_URL, src)

        # Description — paragraphs or any non-bullet text
        desc_parts = []
        for p in block.find_all("p"):
            t = _norm(p.get_text(" ", strip=True))
            if t and "pressure" not in t.lower() and "speed" not in t.lower():
                desc_parts.append(t)

        # Attributes — bullet items with key: value
        attributes = []
        attrs_text_parts = []
        for li in block.find_all("li"):
            t = _norm(li.get_text(" ", strip=True))
            m = re.match(r"^(.+?)[:：]\s*(.+)$", t)
            if m:
                k, v = m.group(1).strip(), m.group(2).strip()
                attributes.append({"name": k, "value": v})
                attrs_text_parts.append(f"{k}: {v}")

        return {
            "code": code,
            "source_url": page_url.rstrip("/") + "/#" + code,
            "image_url": image_url,
            "description": "\n".join(desc_parts),
            "attributes": attributes,
            "attrs_text": " | ".join(attrs_text_parts),
        }

    def _save_card(
        self, session: requests.Session, card: dict, cat: SealCategory, skip_images: bool
    ) -> SealProduct:
        url = card["source_url"]
        obj = SealProduct.objects.filter(source_url=url).first()
        if not obj:
            title = f"Seal profile {card['code']}"
            obj = SealProduct(source_url=url, slug=_unique_slug(title))
        else:
            title = obj.name

        # Build a proper title from code
        name = f"Seal profile {card['code']}"

        obj.name = name
        obj.name_en = name
        obj.category = cat
        obj.subcategory = None
        obj.image_url = card["image_url"]
        obj.description = card["description"]
        obj.attributes = card["attributes"]
        obj.attributes_text = card["attrs_text"]
        obj.is_active = True

        if card["image_url"] and not skip_images:
            try:
                r = session.get(card["image_url"], timeout=20)
                if r.ok:
                    fname = card["image_url"].split("/")[-1].split("?")[0] or "img.gif"
                    obj.image.save(fname, ContentFile(r.content), save=False)
            except Exception:
                pass

        obj.save()
        return obj
