#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  WESTSEAL — Полный парсер каталога + генератор YML-фида         ║
║  Для загрузки товаров/услуг в Яндекс Карты / Яндекс Бизнес     ║
╚══════════════════════════════════════════════════════════════════╝

ЗАПУСК:
    pip install requests beautifulsoup4 lxml
    python westseal_full_parser.py

РЕЗУЛЬТАТ:
    westseal_feed.yml — готовый YML-фид для Яндекс Карт

НАСТРОЙКИ (ниже в коде):
    MAX_PAGES  — макс. страниц на категорию (0 = все)
    DELAY      — задержка между запросами (сек.)
    MODE       — 'profiles' (типы продукции ~500 шт)
                 или 'items' (все позиции ~48 000)
"""

import requests
from bs4 import BeautifulSoup
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent
from datetime import datetime
import time
import re
import sys
import os
import html as html_mod
import logging
import json

# ╔══════════════════ НАСТРОЙКИ ══════════════════╗

BASE_URL = "https://westseal.ru"
OUTPUT_FILE = "westseal_feed.yml"

# Режим: 'profiles' — типы продукции (~500 шт), 'items' — все позиции (~48000)
MODE = "profiles"

# Макс. страниц на категорию (0 = без ограничения)
MAX_PAGES = 0

# Задержка между запросами (секунды)
DELAY = 0.3

# ╚═══════════════════════════════════════════════╝

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("westseal-yml")

# ── Сессия ─────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; WestsealYMLBot/1.0; +https://westseal.ru)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
    "X-Requested-With": "XMLHttpRequest",
})

# ── Категории (актуальные slug'и с сайта) ──────────────────────
CATEGORIES = [
    {"slug": "uplotnenija_porshnja",                     "id": 1,  "name": "Уплотнения поршня"},
    {"slug": "manzhety_gidravlicheskie",                 "id": 2,  "name": "Манжеты гидравлические универсальные"},
    {"slug": "uplotnenija_shtoka",                       "id": 3,  "name": "Уплотнения штока"},
    {"slug": "kolca_uplatnitelnye",                      "id": 4,  "name": "Кольца уплотнительные"},
    {"slug": "grjazesemniki",                            "id": 5,  "name": "Грязесъемники"},
    {"slug": "napravljajuwie_gidrocilindrov",            "id": 6,  "name": "Направляющие гидроцилиндров"},
    {"slug": "manzhety_armirovannye",                    "id": 7,  "name": "Манжеты армированные (сальники)"},
    {"slug": "manzheti_shevronnie",                      "id": 8,  "name": "Шевронные уплотнения и манжеты"},
    {"slug": "pnevmaticheskoe_uplotnenija",              "id": 9,  "name": "Пневматические уплотнения"},
    {"slug": "podsh",                                    "id": 10, "name": "Подшипник скольжения (втулка)"},
    {"slug": "specialnye_uplotnenija",                   "id": 11, "name": "Специальные уплотнения"},
    {"slug": "shaiba",                                   "id": 12, "name": "Шайбы медные"},
    {"slug": "amortizatori_dlya_elektroprivodov_nasosov", "id": 13, "name": "Амортизаторы для электроприводов насосов"},
    {"slug": "koltsa_obzhimnie_usit",                    "id": 14, "name": "Кольца USIT (обжимные)"},
    {"slug": "koltsa_zashchitnye",                       "id": 15, "name": "Кольца защитные"},
    {"slug": "koltsa_stopornye",                         "id": 16, "name": "Кольца стопорные"},
    {"slug": "pnevmaticheskie",                          "id": 17, "name": "Пневматические манжеты"},
    {"slug": "o-kolca",                                  "id": 18, "name": "О-кольца USIT"},
]

PARENT_CAT_ID = 100
PARENT_CAT_NAME = "Уплотнения и комплектующие для гидроцилиндров"


# ── Парсер ─────────────────────────────────────────────────────

def fetch(url, params=None, retries=3):
    """GET-запрос с повторами."""
    for i in range(retries):
        try:
            r = session.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            log.warning(f"  Попытка {i+1}/{retries}: {e}")
            if i < retries - 1:
                time.sleep(2 ** i)
    return None


def parse_profiles(html_text):
    """Парсит профили (типы продукции) из страницы каталога."""
    soup = BeautifulSoup(html_text, "lxml")
    grid = soup.select_one("#catalog-grid")
    if not grid:
        return []

    items = []
    for card in grid.select("a.catalog-card"):
        href = card.get("href", "")
        if not href:
            continue

        # Название из элемента с классом *title*
        title_el = card.select_one("[class*='title']")
        name = title_el.get_text(strip=True) if title_el else ""
        if not name:
            body = card.select_one(".catalog-body")
            if body:
                name = body.get_text(strip=True).split("\n")[0].strip()

        # Картинка
        img = ""
        thumb = card.select_one(".catalog-thumb")
        if thumb and thumb.get("style"):
            m = re.search(r"url\(['\"]?([^'\")\s]+)", thumb["style"])
            if m and "hero.webp" not in m.group(1):
                img = m.group(1)
                if not img.startswith("http"):
                    img = BASE_URL + img

        url = href if href.startswith("http") else BASE_URL + href

        if name and len(name) > 1:
            items.append({"name": name, "url": url, "image": img})

    return items


def parse_items_from_import(html_text):
    """Парсит конкретные товары из панели 'последних импортов' на странице."""
    soup = BeautifulSoup(html_text, "lxml")
    items = []
    for a in soup.select("a.catalog-import-item"):
        href = a.get("href", "")
        name_el = a.select_one(".catalog-import-name")
        name = name_el.get_text(strip=True) if name_el else ""

        img = ""
        thumb = a.select_one(".catalog-import-thumb")
        if thumb and thumb.get("style"):
            m = re.search(r"url\(['\"]?([^'\")\s]+)", thumb["style"])
            if m and "hero.webp" not in m.group(1):
                img = m.group(1)
                if not img.startswith("http"):
                    img = BASE_URL + img

        url = href if href.startswith("http") else BASE_URL + href
        if name and len(name) > 2:
            items.append({"name": name, "url": url, "image": img})

    return items


def get_total_pages(html_text):
    """Определяет количество страниц пагинации."""
    m = re.search(r"Стр\.\s*\d+\s*/\s*(\d+)", html_text)
    return int(m.group(1)) if m else 1


def scrape_category(cat):
    """Собирает все элементы из категории."""
    slug, cat_id, cat_name = cat["slug"], cat["id"], cat["name"]
    log.info(f"📂 {cat_name} ({slug})")

    all_items = []
    page = 1

    while True:
        params = {"category": slug, "page": page}
        html_text = fetch(f"{BASE_URL}/catalog/", params=params)
        if not html_text:
            log.error(f"  ❌ Не удалось загрузить страницу {page}")
            break

        if page == 1:
            total_pages = get_total_pages(html_text)
            max_p = total_pages if MAX_PAGES == 0 else min(total_pages, MAX_PAGES)
            log.info(f"  📄 Всего страниц: {total_pages} (обработаем: {max_p})")

        # Парсим в зависимости от режима
        if MODE == "profiles":
            items = parse_profiles(html_text)
        else:
            items = parse_profiles(html_text)
            items += parse_items_from_import(html_text)

        if not items:
            break

        for item in items:
            item["cat_id"] = cat_id
            item["cat_name"] = cat_name

        all_items.extend(items)

        if page % 10 == 0:
            log.info(f"  📄 Стр. {page}/{max_p} — собрано {len(all_items)}")

        page += 1
        if MAX_PAGES > 0 and page > MAX_PAGES:
            break
        if page > total_pages:
            break

        time.sleep(DELAY)

    log.info(f"  ✅ Итого: {len(all_items)} позиций")
    return all_items


# ── Генератор YML ─────────────────────────────────────────────

def esc(text):
    return html_mod.escape(str(text), quote=True) if text else ""


def generate_yml(all_items, output_path):
    """Генерирует YML-файл (Yandex Market Language)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    root = Element("yml_catalog", date=now)
    shop = SubElement(root, "shop")

    SubElement(shop, "name").text = "WESTSEAL"
    SubElement(shop, "company").text = "WESTSEAL — гидравлические и пневматические уплотнения"
    SubElement(shop, "url").text = BASE_URL

    # Валюты
    currencies = SubElement(shop, "currencies")
    SubElement(currencies, "currency", id="RUR", rate="1")

    # Категории
    categories_el = SubElement(shop, "categories")
    SubElement(categories_el, "category", id=str(PARENT_CAT_ID)).text = PARENT_CAT_NAME
    for cat in CATEGORIES:
        SubElement(
            categories_el, "category",
            id=str(cat["id"]),
            parentId=str(PARENT_CAT_ID),
        ).text = cat["name"]

    # Оферты
    offers_el = SubElement(shop, "offers")
    seen = set()
    oid = 1

    for item in all_items:
        if item["url"] in seen:
            continue
        seen.add(item["url"])

        offer = SubElement(offers_el, "offer", id=str(oid), available="true")
        SubElement(offer, "name").text = f"{item['name']} — {item['cat_name']}"
        SubElement(offer, "url").text = item["url"]
        SubElement(offer, "price").text = "1"
        SubElement(offer, "currencyId").text = "RUR"
        SubElement(offer, "categoryId").text = str(item["cat_id"])

        if item.get("image"):
            SubElement(offer, "picture").text = item["image"]

        SubElement(offer, "description").text = (
            f"{item['name']}. {item['cat_name']}. "
            "Цена по запросу. "
            "Для уточнения цены и наличия свяжитесь с менеджером WESTSEAL."
        )

        param = SubElement(offer, "param", name="Цена")
        param.text = "По запросу"

        oid += 1

    # Запись
    indent(root, space="  ")
    tree = ElementTree(root)

    with open(output_path, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<!DOCTYPE yml_catalog SYSTEM "shops.dtd">\n')
        tree.write(f, encoding="UTF-8", xml_declaration=False)

    return oid - 1


# ── Точка входа ────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("  WESTSEAL YML Feed Generator")
    log.info(f"  Режим: {MODE} | Макс. страниц: {MAX_PAGES or 'все'}")
    log.info("=" * 60)

    all_items = []
    for cat in CATEGORIES:
        try:
            items = scrape_category(cat)
            all_items.extend(items)
        except Exception as e:
            log.error(f"  Ошибка: {e}")

    log.info(f"\n📊 Всего собрано: {len(all_items)}")

    if not all_items:
        log.error("❌ Ничего не найдено. Проверьте доступность westseal.ru")
        sys.exit(1)

    # Сохраняем промежуточный JSON (на случай повторной генерации)
    json_path = OUTPUT_FILE.replace(".yml", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    log.info(f"💾 JSON сохранён: {json_path}")

    # Генерация YML
    count = generate_yml(all_items, OUTPUT_FILE)
    size = os.path.getsize(OUTPUT_FILE)

    log.info("")
    log.info("=" * 60)
    log.info(f"  ✅ YML-фид: {OUTPUT_FILE}")
    log.info(f"     Уникальных товаров: {count}")
    log.info(f"     Размер: {size / 1024 / 1024:.2f} МБ")
    log.info("=" * 60)
    log.info("")
    log.info("📌 Следующие шаги:")
    log.info("   1. Загрузите файл на ваш сервер")
    log.info("      Пример: https://westseal.ru/feed/westseal_feed.yml")
    log.info("   2. Откройте Яндекс Бизнес → Продвижение → Рекламные материалы")
    log.info("   3. В блоке «Товары и услуги» нажмите «настройте YML-фид»")
    log.info("   4. Вставьте ссылку на файл и дождитесь проверки")
    log.info("")
    log.info("💡 Совет: настройте cron/планировщик для обновления фида раз в день:")
    log.info("   0 3 * * * python3 /path/to/westseal_full_parser.py")


if __name__ == "__main__":
    main()
