вimport json
import os
import urllib.request
import shutil
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "catalogs")
FILES_DIR = os.path.join(DATA_DIR, "files")

os.makedirs(FILES_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "sources.json"), "r", encoding="utf-8") as f:
    sources = json.load(f)

for item in sources:
    url = item["url"]
    if item.get("skip_download"):
        print("skip (flag)", url)
        continue
    filename = item.get("filename")
    if not filename:
        path = urlparse(url).path
        filename = os.path.basename(path)
    dest = os.path.join(FILES_DIR, filename)
    if os.path.exists(dest):
        print("skip", filename)
        item["local_path"] = f"data/catalogs/files/{filename}"
        continue
    print("download", url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)
        item["local_path"] = f"data/catalogs/files/{filename}"
    except Exception as e:
        print("failed", url, e)

with open(os.path.join(DATA_DIR, "sources.json"), "w", encoding="utf-8") as f:
    json.dump(sources, f, ensure_ascii=False, indent=2)
