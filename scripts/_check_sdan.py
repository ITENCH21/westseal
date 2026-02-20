import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django; django.setup()
from apps.core.models import SealProduct

p = SealProduct.objects.filter(name__icontains='SDAN').first()
if p:
    print(f"Продукт: {p.name}")
    print(f"Slug: {p.slug}")
    print(f"source_url: {p.source_url}")
    print(f"Атрибуты: {p.attributes}")
else:
    print("Product not found")

# Проверяем несколько mkt-rti продуктов с пустыми атрибутами
print("\n--- mkt-rti примеры атрибутов ---")
from apps.core.models import SealProduct
import json
for p in SealProduct.objects.filter(source_url__icontains='mkt-rti').exclude(attributes=None)[:5]:
    print(f"\n{p.name}:")
    print(f"  attrs: {p.attributes[:3] if isinstance(p.attributes, list) else p.attributes}")
