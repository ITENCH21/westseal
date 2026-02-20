"""
Переносит krpms-продукты из krpms-* категорий в существующие общие разделы.
Деактивирует все krpms-* категории.

Запуск: python scripts/_fix_krpms_categories.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from apps.core.models import SealProduct, SealCategory

# krpms_slug → существующий generic slug
MAPPING = {
    'krpms-gryazesemniki':              'grjazesemniki',
    'krpms-uplotneniya-shtoka':         'uplotnenija_shtoka',
    'krpms-uplotneniya-porshnya':       'uplotnenija_porshnja',
    'krpms-napravlyayuschie':           'napravljajuwie_gidrocilindrov',
    'krpms-o-koltca':                   'kolca_uplatnitelnye',
    'krpms-opornye-koltsa':             'napravljajuwie_gidrocilindrov',
    'krpms-pnevmaticheskie-uplotneniya':'pnevmaticheskoe_uplotnenija',
    'krpms-rotornye-uplotneniya':       'specialnye_uplotnenija',
    'krpms-simmetrichnye-uplotneniya':  'manzhety_gidravlicheskie',
    'krpms-staticheskie-uplotneniya':   'kolca_uplatnitelnye',
    'krpms-uplotneniya-dlya-gornoy':    'specialnye_uplotnenija',
}

moved_total = 0

for krpms_slug, generic_slug in MAPPING.items():
    krpms_cat = SealCategory.objects.filter(slug=krpms_slug).first()
    if not krpms_cat:
        print(f'[SKIP] {krpms_slug}: не найдена')
        continue

    generic_cat = SealCategory.objects.filter(slug=generic_slug).first()
    if not generic_cat:
        print(f'[ERROR] Целевой раздел {generic_slug} не найден!')
        continue

    products = SealProduct.objects.filter(category=krpms_cat)
    cnt = products.count()
    if cnt > 0:
        products.update(category=generic_cat)
        print(f'[OK] {krpms_slug} → {generic_slug}: перенесено {cnt} продуктов')
        moved_total += cnt
    else:
        print(f'[SKIP] {krpms_slug}: 0 продуктов')

    # Деактивируем krpms-* категорию
    krpms_cat.is_active = False
    krpms_cat.save(update_fields=['is_active'])

print(f'\nИтого перенесено: {moved_total} продуктов')

# Деактивируем все оставшиеся krpms-* категории (на всякий случай)
remaining = SealCategory.objects.filter(slug__startswith='krpms-', is_active=True)
if remaining.exists():
    slugs = list(remaining.values_list('slug', flat=True))
    remaining.update(is_active=False)
    print(f'Деактивированы дополнительно: {slugs}')

print('\n=== Итоговые активные категории ===')
for cat in SealCategory.objects.filter(is_active=True, parent__isnull=True).order_by('name'):
    cnt = cat.products.filter(is_active=True).count()
    print(f'  [{cnt:5d}] {cat.name}  ({cat.slug})')
