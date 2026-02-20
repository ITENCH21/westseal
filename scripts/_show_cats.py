"""Show all DB categories."""
import django, os, sys
sys.path.insert(0, "/Users/ivan/евро сеал")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from apps.core.models import SealCategory, SealProduct
for c in SealCategory.objects.filter(is_active=True).order_by('slug'):
    cnt = SealProduct.objects.filter(category=c).count()
    print(f"  {c.slug:45s} | {c.name[:40]:40s} | {cnt} prods")
print(f"\nTotal: {SealCategory.objects.filter(is_active=True).count()} active cats")
print(f"Total products: {SealProduct.objects.count()}")
