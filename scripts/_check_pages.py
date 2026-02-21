import django, os, sys
sys.path.insert(0, '/Users/ivan/евро сеал')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.core.models import Page

pages = Page.objects.all()
for p in pages:
    hero_en = p.hero_subtitle_en or ''
    print(f'slug={p.slug!r} hero_subtitle_ru={p.hero_subtitle_ru!r}')
    print(f'  hero_subtitle_en={hero_en!r}')
