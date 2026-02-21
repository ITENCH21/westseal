import django, os, sys
sys.path.insert(0, '/Users/ivan/евро сеал')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.core.models import SealCategory, SiteSettings

cats = SealCategory.objects.filter(parent=None)
print('TOP CATEGORIES:')
for c in cats:
    print(f'  {c.slug}: {c.name!r}')
    for sub in c.children.all()[:5]:
        print(f'    sub: {sub.slug}: {sub.name!r}')

s = SiteSettings.load()
print(f'\norg_legal_en={s.org_legal_en!r}')
print(f'address_en={s.address_en!r}')
