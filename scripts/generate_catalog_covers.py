import os
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "catalogs" / "sources.json"
OUT_DIR = BASE_DIR / "data" / "catalogs" / "covers"
OUT_DIR.mkdir(parents=True, exist_ok=True)

palette = {
    "hydraulic": ("#1f4a8a", "#d1373d"),
    "pneumatic": ("#2c5aa0", "#f28b30"),
    "rotary": ("#1b3358", "#d1373d"),
    "oring": ("#3a5f9b", "#b92f35"),
    "kits": ("#1f4a8a", "#b92f35"),
    "other": ("#2b2f3a", "#d1373d"),
}

items = json.loads(DATA_PATH.read_text(encoding="utf-8"))

for item in items:
    title = item.get("title_ru") or item.get("title_en") or "Catalog"
    manufacturer = item.get("manufacturer", "WESTSEAL")
    category = item.get("category", "other")
    c1, c2 = palette.get(category, palette["other"])
    filename = (item.get("filename") or "catalog").replace(".pdf", "") + ".svg"
    out_path = OUT_DIR / filename

    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="18" flood-color="#b43a3a" flood-opacity="0.35"/>
    </filter>
  </defs>
  <rect width="800" height="450" fill="#0f1424"/>
  <rect x="30" y="30" width="740" height="390" rx="28" fill="url(#g)" filter="url(#shadow)"/>
  <circle cx="650" cy="140" r="90" fill="rgba(255,255,255,0.15)"/>
  <circle cx="650" cy="140" r="55" fill="none" stroke="rgba(255,255,255,0.45)" stroke-width="16"/>
  <text x="70" y="120" fill="#ffffff" font-size="28" font-family="Manrope, Arial, sans-serif" letter-spacing="1">WESTSEAL</text>
  <text x="70" y="185" fill="#ffffff" font-size="36" font-family="Manrope, Arial, sans-serif" font-weight="700">{title}</text>
  <text x="70" y="230" fill="#f7f7f7" font-size="20" font-family="Manrope, Arial, sans-serif">{manufacturer} · {category.upper()}</text>
  <text x="70" y="360" fill="#f7f7f7" font-size="16" font-family="Manrope, Arial, sans-serif">Updated {datetime.now().strftime('%Y-%m-%d')}</text>
</svg>
""".strip()

    out_path.write_text(svg, encoding="utf-8")
    item["cover_svg"] = str(out_path.relative_to(BASE_DIR))

DATA_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Generated {len(items)} covers in {OUT_DIR}")
