"""Диагностика расхождения счётчиков товаров в категориях."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from apps.core.models import SealProduct, SealCategory
from django.db.models import Count

print("=== Все категории: total / active ===")
for c in SealCategory.objects.all().order_by('name'):
    total  = SealProduct.objects.filter(category=c).count()
    active = SealProduct.objects.filter(category=c, is_active=True).count()
    flag = " <<< РАСХОЖДЕНИЕ" if total != active else ""
    print(f"  [{c.slug:30s}] {c.name:35s} total={total:4d}  active={active:4d}{flag}")

print()
total_all  = SealProduct.objects.count()
total_act  = SealProduct.objects.filter(is_active=True).count()
print(f"ИТОГО: {total_all} товаров, из них active={total_act}, inactive={total_all - total_act}")
