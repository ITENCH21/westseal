import os, sys
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django; django.setup()
from apps.core.models import SealProduct, SealCategory

shtoka = SealCategory.objects.filter(slug='uplotnenija_shtoka').first()
total = SealProduct.objects.filter(category=shtoka).count()
krpms_shtoka = SealProduct.objects.filter(category=shtoka, source_url__icontains='krpms').count()
krpms_with_sub = SealProduct.objects.filter(category=shtoka, source_url__icontains='krpms', subcategory__isnull=False).count()
print(f'Всего в Уплотнения штока: {total}')
print(f'krpms в Уплотнения штока: {krpms_shtoka}')
print(f'krpms с subcategory: {krpms_with_sub}')

rs01_sub = SealCategory.objects.filter(code='RS01', parent=shtoka).first()
if rs01_sub:
    prods = SealProduct.objects.filter(subcategory=rs01_sub)
    print(f'\nПродукты RS01 (всего {prods.count()}):')
    for p in prods[:5]:
        print(f'  {p.name} | {p.source_url}')

rs01_prods = SealProduct.objects.filter(category=shtoka, source_url__icontains='krpms', attributes__icontains='RS01')
print(f'\nkrpms shtoka с RS01 в атрибутах: {rs01_prods.count()}')
for p in rs01_prods[:3]:
    print(f'  slug={p.slug} | sub={p.subcategory}')
    print(f'  attrs={p.attributes[:200]}')
