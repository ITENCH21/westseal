"""
Создаёт подкатегории-профили для krpms-продуктов и назначает subcategory.

Логика:
- Извлекаем profile code из атрибута "Код уплотнения": "Kastas K05" → "K05",
  "KRPMS RS01" → "RS01", "ASTON SA" → "SA"
- Создаём SealCategory(parent=product.category, code=profile_code) если нет
- Присваиваем product.subcategory = эта подкатегория

Запуск: python scripts/_assign_krpms_profiles.py
"""
import re
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from apps.core.models import SealProduct, SealCategory

# Известные бренды для отсечения из кода
BRANDS = ["Aston Seals", "Kastas", "KRPMS", "ASTON", "kastas", "krpms"]

def extract_profile_code(attrs: list, name: str) -> str:
    """Извлечь код профиля из атрибутов или имени продукта."""
    brand = ""
    code_raw = ""
    for a in (attrs or []):
        aname = a.get("name", "")
        aval = (a.get("value") or "").strip()
        if "Производитель" in aname:
            brand = aval
        elif "Код" in aname and aval:
            code_raw = aval

    if code_raw:
        # Убираем бренд-prefix из кода
        stripped = code_raw
        for b in BRANDS:
            if stripped.lower().startswith(b.lower()):
                stripped = stripped[len(b):].strip()
                break
        if brand:
            if stripped.lower().startswith(brand.lower()):
                stripped = stripped[len(brand):].strip()
        if stripped:
            return stripped.upper()

    # Фолбэк: последнее слово имени продукта, если оно похоже на код (всё заглавное / буквы+цифры)
    last = name.strip().split()[-1] if name.strip() else ""
    if last and re.match(r'^[A-Z0-9][A-Z0-9\-]{1,10}$', last.upper()):
        return last.upper()
    return ""


# Кеш subcategory: (category_id, code) → SealCategory
subcat_cache: dict = {}

def get_or_create_subcat(parent: SealCategory, code: str) -> SealCategory:
    key = (parent.pk, code)
    if key not in subcat_cache:
        slug = f"{parent.slug}-{code.lower().replace(' ', '-')}"
        obj, created = SealCategory.objects.get_or_create(
            slug=slug,
            defaults={
                "name": code,
                "code": code,
                "parent": parent,
                "is_active": True,
            }
        )
        if not created:
            changed = False
            if obj.code != code:
                obj.code = code; changed = True
            if not obj.is_active:
                obj.is_active = True; changed = True
            if obj.parent_id != parent.pk:
                obj.parent = parent; changed = True
            if changed:
                obj.save()
        elif created:
            print(f"  Created subcat: {slug} (code={code}) under {parent.slug}")
        subcat_cache[key] = obj
    return subcat_cache[key]


# --- Main ---
qs = SealProduct.objects.filter(
    source_url__icontains='krpms.ru',
    subcategory__isnull=True,
    is_active=True,
).select_related('category')

total = qs.count()
print(f"krpms продуктов без subcategory: {total}")

assigned = 0
skipped = 0

for p in qs:
    if not p.category:
        skipped += 1
        continue
    code = extract_profile_code(p.attributes, p.name)
    if not code:
        print(f"  [SKIP no code] {p.slug}: {p.name[:50]}")
        skipped += 1
        continue
    subcat = get_or_create_subcat(p.category, code)
    p.subcategory = subcat
    p.save(update_fields=["subcategory"])
    assigned += 1

print(f"\nИтого: назначено={assigned}, пропущено={skipped}")

# Итог
print("\n=== Профили (subcategories) krpms-продуктов по категориям ===")
created_subcats = SealCategory.objects.filter(
    slug__regex=r'.+-[a-z0-9]',
    parent__isnull=False,
    is_active=True,
).exclude(
    parent__slug__startswith='krpms-'
).filter(
    sub_products__source_url__icontains='krpms.ru'
).distinct().order_by('parent__name', 'code')

for sub in created_subcats:
    cnt = sub.sub_products.filter(source_url__icontains='krpms.ru').count()
    print(f"  [{cnt:3d}] {sub.parent.name} / {sub.code}  ({sub.slug})")
