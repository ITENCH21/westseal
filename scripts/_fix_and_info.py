"""
Quick helper: show empty categories and fix literal \\n in descriptions.
Run: python scripts/_fix_and_info.py
"""
import django, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.core.models import SealCategory, SealProduct

print("=== Разделы (пустые помечены *) ===")
for c in SealCategory.objects.filter(parent__isnull=True).order_by("name"):
    cnt = c.products.filter(is_active=True).count()
    marker = " *" if cnt == 0 else ""
    print(f"  [{c.slug}]  {c.name}: {cnt} товаров{marker}  url={c.source_url}")

print()
print("=== Фикс literal \\n в описаниях ===")
qs = SealProduct.objects.filter(description__contains="\\n")
total = qs.count()
print(f"Найдено {total} продуктов с literal \\n")
fixed = 0
for p in qs.iterator():
    new_desc = p.description.replace("\\n", "\n")
    if new_desc != p.description:
        p.description = new_desc
        p.save(update_fields=["description"])
        fixed += 1
print(f"Исправлено: {fixed}")
