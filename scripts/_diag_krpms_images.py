"""Диагностика изображений krpms-товаров."""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.core.models import SealProduct

total = SealProduct.objects.filter(source_url__contains='krpms.ru').count()
no_img = SealProduct.objects.filter(source_url__contains='krpms.ru', image='').count()
with_img = SealProduct.objects.filter(source_url__contains='krpms.ru').exclude(image='').count()
print(f"krpms: total={total}, no_image_file={no_img}, with_image_file={with_img}")

for p in SealProduct.objects.filter(source_url__contains='krpms.ru')[:10]:
    print(f"  name={p.name[:40]}")
    print(f"    image_url={p.image_url[:100] if p.image_url else 'NONE'}")
    print(f"    image_file={p.image.name if p.image else 'NONE'}")
