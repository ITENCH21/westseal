"""Диагностика расхождения счётчиков на плитке vs при открытии."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from apps.core.models import SealProduct, SealCategory
from django.db.models import Count, Q

# --- Ищем "Шайбы медные" ---
cat = SealCategory.objects.filter(slug='shaiba').first()
if not cat:
    print("Категория не найдена!")
    exit()

print(f"Категория: [{cat.id}] {cat.name!r} slug={cat.slug!r} parent={cat.parent}")
print()

# Считаем как views.py считает product_count на плитке
via_category_fk    = SealProduct.objects.filter(category=cat, is_active=True).count()
via_subcategory_fk = SealProduct.objects.filter(subcategory=cat, is_active=True).count()
print(f"via category FK     (related='products'):     {via_category_fk}")
print(f"via subcategory FK  (related='sub_products'): {via_subcategory_fk}")
print()

# Считаем как аннотация views.py (через ORM)
cats_annot = (
    SealCategory.objects.filter(id=cat.id)
    .annotate(product_count=Count("products", filter=Q(products__is_active=True), distinct=True))
    .annotate(child_count=Count("children", filter=Q(children__is_active=True), distinct=True))
    .first()
)
print(f"annotated product_count (tile показывает): {cats_annot.product_count}")
print(f"annotated child_count  (Профили на плитке):  {cats_annot.child_count}")
print()

# Дочерние категории
children = SealCategory.objects.filter(parent=cat)
print(f"Дочерних категорий: {children.count()}")
for child in children:
    c_via_cat = SealProduct.objects.filter(category=child, is_active=True).count()
    c_via_sub = SealProduct.objects.filter(subcategory=child, is_active=True).count()
    print(f"  [{child.id}] {child.name!r} | via category={c_via_cat} | via subcategory={c_via_sub}")

print()

# Посмотрим первые 5 товаров
print("=== Первые 5 товаров (category=Шайбы медные) ===")
for p in SealProduct.objects.filter(category=cat, is_active=True)[:5]:
    print(f"  [{p.id}] {p.name!r} | sub={getattr(p.subcategory,'name','None')!r}")

print()
print("=== Первые 5 товаров через subcategory ===")
for p in SealProduct.objects.filter(subcategory=cat, is_active=True)[:5]:
    print(f"  [{p.id}] {p.name!r} | cat_field={getattr(p.category,'name','None')!r}")
