"""
Fix descriptions: strip leading 'Описание' header line captured by scraper.
Run: python scripts/_fix_desc_header.py
"""
import django, os, sys, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection, OperationalError
from apps.core.models import SealProduct

# Enable SQLite busy timeout (30 sec) to wait instead of failing immediately
with connection.cursor() as c:
    c.execute("PRAGMA busy_timeout = 30000;")

fixed = 0
to_fix = []
for p in SealProduct.objects.exclude(description="").only("id", "description"):
    cleaned = re.sub(r"^\s*Описание\s*\n+", "", p.description, flags=re.IGNORECASE)
    if cleaned != p.description:
        p.description = cleaned
        to_fix.append(p)

if to_fix:
    # bulk_update in batches of 200 to minimize lock time
    for i in range(0, len(to_fix), 200):
        batch = to_fix[i:i+200]
        for attempt in range(5):
            try:
                SealProduct.objects.bulk_update(batch, ["description"])
                fixed += len(batch)
                break
            except OperationalError as e:
                if "locked" in str(e):
                    print(f"DB locked, retry {attempt+1}...")
                    time.sleep(3)
                else:
                    raise

print(f"Исправлено заголовков 'Описание': {fixed}")
