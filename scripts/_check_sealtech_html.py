"""Debug: check what HTML requests actually gets from seal-tech.ru listing page."""
import urllib.parse
import requests
from bs4 import BeautifulSoup

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.8",
})

url = "https://seal-tech.ru/katalog/proizvodstvo-uplotnenijj/porshnevye-uplotneniya/"
r = session.get(url, timeout=30)
html = r.text
soup = BeautifulSoup(html, "html.parser")

all_links = soup.find_all("a", href=True)
print(f"Total <a> tags: {len(all_links)}")

catalog_links = [a["href"] for a in all_links if "/katalog/" in a.get("href", "")]
print(f"Katalog links: {len(catalog_links)}")

section_path = "/katalog/proizvodstvo-uplotnenijj/porshnevye-uplotneniya/"
product_links = []
for h in catalog_links:
    path = urllib.parse.urlparse(h.split("#")[0]).path
    if path.startswith(section_path):
        relative = path[len(section_path):].strip("/")
        if "/" not in relative and relative:
            product_links.append(path)

print(f"\nProduct links (matching section pattern): {len(product_links)}")
for p in product_links:
    print(f"  {p}")

# Show ALL katalog links to understand structure
print("\nAll /katalog/ links:")
for h in sorted(set(catalog_links)):
    path = urllib.parse.urlparse(h.split("#")[0]).path
    parts = [p for p in path.split("/") if p]
    print(f"  depth={len(parts)}  {path}")

# Also print a snippet of the raw HTML around "ps0" if it appears
lower = html.lower()
idx = lower.find("ps0")
if idx >= 0:
    print(f"\nHTML around 'ps0' (chars {max(0,idx-200)} to {idx+400}):")
    print(html[max(0, idx-200):idx+400])
else:
    print("\n'ps0' NOT found in raw HTML — products likely loaded by JS")
    # Print first 2000 chars for context
    print("\nFirst 2000 chars of HTML:")
    print(html[:2000])
