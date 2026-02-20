"""Диагностика структуры spb-rezina.ru"""
import os, sys, re, html, urllib.parse
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

BASE = "https://spb-rezina.ru"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# ── 1. Подкатегории Манжет/Сальников/Колец
print("=" * 60)
print("SUBCATEGORIES of path=4")
r = S.get(f"{BASE}/index.php", params={"route": "product/category", "path": "4"}, timeout=20)
for m in re.finditer(r'href="([^"]*path=4_(\d+)[^"]*)"[^>]*>\s*([^<]{2,})', r.text):
    url, sub_id, name = m.group(1), m.group(2), html.unescape(m.group(3)).strip()
    if name and len(name) < 60:
        print(f"  path=4_{sub_id}  {name}")

# ── 2. Товары из первой подкатегории (Кольца = 446)
print("\n" + "=" * 60)
print("PRODUCTS from path=4_446 (page 1)")
r2 = S.get(f"{BASE}/index.php", params={"route": "product/category", "path": "4_446"}, timeout=20)
prod_ids = re.findall(r'route=product/product[^"]*product_id=(\d+)', r2.text)
seen = []
for pid in prod_ids:
    if pid not in seen:
        seen.append(pid)
print(f"  Found {len(seen)} product IDs: {seen[:8]}...")

# ── 3. Пагинация
pages = re.findall(r'href="([^"]*page=(\d+)[^"]*)"', r2.text)
print(f"  Pagination links found: {len(pages)}")
for url, pg in pages[:5]:
    print(f"  page={pg} -> {html.unescape(url)[:80]}")

# ── 4. Структура одного товара
print("\n" + "=" * 60)
print("PRODUCT DETAIL for product_id=1677")
r3 = S.get(f"{BASE}/index.php", params={"route": "product/product", "path": "4_446", "product_id": "1677"}, timeout=20)
content = r3.text

# title
t = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.S)
print("  Title:", html.unescape(re.sub(r'<[^>]+>', '', t.group(1))).strip() if t else "NOT FOUND")

# images (main)
for pat in [r'id=["\']image["\'][^>]*src=["\']([^"\']+)["\']',
            r'<img[^>]+id=["\']main-image["\'][^>]+src=["\']([^"\']+)',
            r'<a[^>]+data-fancybox[^>]+href=["\']([^"\']+)["\']',
            r'image/cache/data/[^"\'>\s]+\.jpg']:
    m = re.search(pat, content, re.I)
    if m:
        print("  Image:", m.group(0 if pat.endswith('jpg') else 1)[:100])
        break

# attributes
rows = re.findall(r'<tr>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', content, re.S)
print(f"  Attributes ({len(rows)} rows):")
for name_raw, val_raw in rows[:15]:
    n = html.unescape(re.sub(r'<[^>]+>', '', name_raw)).strip()
    v = html.unescape(re.sub(r'<[^>]+>', '', val_raw)).strip()
    if n and v and 2 < len(n) < 60:
        print(f"    {n!r}: {v!r}")

# description tabs
for tab_id in ["tab-description", "description", "product-tab-description", "tab-attribute"]:
    m = re.search(rf'id="{tab_id}"(.*?)</div>', content, re.S)
    if m:
        raw = re.sub(r'<[^>]+>', ' ', m.group(1))
        clean = html.unescape(raw).strip()[:300]
        if clean:
            print(f"  Description [{tab_id}]:", clean[:200])
            break

# SKU/артикул
sku = re.search(r'(артикул|sku|SKU|Артикул)[^<]{0,10}(?:<[^>]*>)?([A-Za-z0-9\-\.]+)', content, re.I)
print("  SKU:", sku.group(2) if sku else "not found")

print("\nDONE")
