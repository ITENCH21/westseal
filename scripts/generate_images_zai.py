import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

API_KEY = os.environ.get("ZAI_API_KEY")
if not API_KEY:
    raise SystemExit("ZAI_API_KEY is not set")

OUT_DIR = os.path.join("static", "img", "ai")
os.makedirs(OUT_DIR, exist_ok=True)

MODEL = "cogView-4-250304"
ENDPOINT = "https://api.z.ai/api/paas/v4/images/generations"

PROMPTS = [
    {
        "name": "hero",
        "size": "1024x1024",
        "prompt": "Hydraulic and pneumatic seals engineering, premium industrial look, metallic cylinder cross-section, red and blue accents, clean technical lighting, high detail, realistic, no text"
    },
    {
        "name": "production",
        "size": "1024x1024",
        "prompt": "Precision manufacturing of seals, CNC machining close-up, blue and red color accents, modern clean factory, cinematic lighting, realistic, no text"
    },
    {
        "name": "materials",
        "size": "1024x1024",
        "prompt": "Collection of industrial seal materials (NBR, FKM, PTFE, PU) arranged on clean surface, red and blue highlights, premium product photography, no text"
    },
    {
        "name": "catalogs",
        "size": "1024x1024",
        "prompt": "Industrial catalog desk scene, hydraulic seals samples, blueprint background, red and blue accents, bright professional look, no text"
    },
    {
        "name": "support",
        "size": "1024x1024",
        "prompt": "Engineer support desk, technical drawings, hydraulic components, modern office, red and blue accents, friendly but professional, no text"
    },
    {
        "name": "warehouse",
        "size": "1024x1024",
        "prompt": "Clean industrial warehouse shelves with seal kits boxes, red and blue labeling, sharp and organized, realistic lighting, no text"
    }
]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

for item in PROMPTS:
    payload = {
        "model": MODEL,
        "prompt": item["prompt"],
        "size": item["size"],
        "quality": "standard",
    }
    req = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    url = data.get("data", [{}])[0].get("url")
    if not url:
        print("Failed to get image URL for", item["name"], data)
        continue
    filename = f"{item['name']}.png"
    out_path = os.path.join(OUT_DIR, filename)
    req_img = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_img, timeout=60) as img_resp, open(out_path, "wb") as out:
        out.write(img_resp.read())
    print("Saved", out_path)
