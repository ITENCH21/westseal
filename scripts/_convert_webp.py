#!/usr/bin/env python3
"""Convert PNG images used in templates to WebP."""
import os
import sys

# Run from project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

IMG_DIR = "static/img/ai"
images = [
    "catalogs.png", "contacts-delivery.png", "cylinder_cutaway.png",
    "hero.png", "materials.png", "production.png",
    "products_guides.png", "products_kits.png", "products_orings.png",
    "products_piston.png", "products_rod.png", "products_wiper.png",
    "warehouse.png",
    "грязесьемники.png", "пневматические.png", "ремкомплект.png",
]

for fname in images:
    src = os.path.join(IMG_DIR, fname)
    if not os.path.exists(src):
        print(f"SKIP (not found): {fname}")
        continue
    dst = os.path.join(IMG_DIR, os.path.splitext(fname)[0] + ".webp")
    with Image.open(src) as im:
        w, h = im.size
        im.save(dst, "WEBP", quality=85, method=6)
        orig_size = os.path.getsize(src)
        new_size = os.path.getsize(dst)
        pct = int((1 - new_size / orig_size) * 100)
        print(f"OK {fname} {w}x{h}  {orig_size//1024}KB -> {new_size//1024}KB ({pct}% smaller)")

print("Done.")
