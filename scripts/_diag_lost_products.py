"""Показывает все категории где есть прямые продукты (category FK) но нет subcategory — они теряются."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from apps.core.models import SealProduct, SealCategory
from django.db.models import Count, Q

print("=== Родительские категории с прямыми products (category FK) ===")
parents = SealCategory.objects.filter(parent__isnull=True, is_active=True)
for c in parents.order_by('name'):
    direct = SealProduct.objects.filter(category=c, is_active=True).count()
    sub_cnt = SealCategory.objects.filter(parent=c, is_active=True).count()
    via_sub  = SealProduct.objects.filter(subcategory__parent=c, is_active=True).count()
    # Количество прямых товаров без subcategory
    no_sub   = SealProduct.objects.filter(category=c, is_active=True, subcategory__isnull=True).count()
    if direct > 0:
        flag = " <<< ТЕРЯЮТСЯ" if sub_cnt > 0 and no_sub > 0 else ""
        print(f"  [{c.slug:30s}] {c.name:30s} | direct={direct:4d} | sub_cats={sub_cnt} | lost_products={no_sub}{flag}")
