"""Quick check: look at descriptions of штоковые уплотнения 2-series to see if cleanup was appropriate."""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import sys
sys.path.insert(0, "/Users/ivan/евро сеал")
django.setup()

from apps.core.models import SealProduct

# Check a few штоковые уплотнения
for p in SealProduct.objects.filter(name__icontains="2-028")[:3]:
    print(f"=== {p.name} ===")
    print(f"  description: {p.description[:300] if p.description else 'EMPTY'}")
    print()

# Also show products that have non-empty descriptions from krpms
for p in SealProduct.objects.filter(source_url__contains='krpms.ru').exclude(description='')[:3]:
    print(f"=== krpms: {p.name} ===")
    print(f"  description: {p.description[:300]}")
    print()
