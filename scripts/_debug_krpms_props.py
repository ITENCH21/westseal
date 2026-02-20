"""Debug: show HTML structure of krpms properties section."""
import requests
from bs4 import BeautifulSoup, Tag

url = "https://www.krpms.ru/catalog/uplotneniya/gryazesemniki/gryazesemnik-krpms/gryazesyemnik-wr01.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru",
}
html = requests.get(url, headers=headers, timeout=20).text
soup = BeautifulSoup(html, "html.parser")

print("=== Searching for property headings ===")
for h in soup.find_all(["h2", "h3"]):
    t = h.get_text(strip=True)
    if any(k in t.lower() for k in ("свойств", "характеристик", "параметр")):
        print(f"\nHEADING: <{h.name}> '{t}'")
        count = 0
        for sib in h.next_siblings:
            if not isinstance(sib, Tag):
                continue
            count += 1
            classes = sib.get("class") or []
            txt = sib.get_text(strip=True)[:120]
            print(f"  SIB {count}: <{sib.name}> class={classes}  text='{txt}'")
            # Show children
            for i, child in enumerate(sib.children):
                if not isinstance(child, Tag):
                    continue
                if i > 6:
                    break
                child_classes = child.get("class") or []
                child_txt = child.get_text(strip=True)[:80]
                print(f"    CHILD <{child.name}> class={child_classes}  text='{child_txt}'")
                # grandchildren
                for j, gc in enumerate(child.children):
                    if not isinstance(gc, Tag):
                        continue
                    if j > 3:
                        break
                    gc_txt = gc.get_text(strip=True)[:60]
                    print(f"      GC <{gc.name}> class={gc.get('class')}  text='{gc_txt}'")
            if count >= 5:
                break

print("\n=== Tables on page ===")
for i, tbl in enumerate(soup.find_all("table")):
    rows = tbl.find_all("tr")
    if rows:
        first = rows[0].get_text(strip=True)[:80]
        print(f"Table {i}: {len(rows)} rows, first='{first}'")
