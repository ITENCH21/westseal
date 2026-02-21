#!/usr/bin/env python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.core.models import Article, FAQItem, CaseStudy, Page, SiteSettings, CatalogPDF, Testimonial

print("=== Articles ===")
for a in Article.objects.all():
    te = bool(a.title_en)
    be = bool(a.body_en)
    print(f"  {a.slug}: title_en={'OK' if te else 'EMPTY'}, body_en={'OK('+str(len(a.body_en))+')' if be else 'EMPTY'}")

print()
print("=== FAQItems ===")
empty = 0
for f in FAQItem.objects.all():
    if not f.question_en or not f.answer_en:
        empty += 1
        print(f"  id={f.id}: q_en={'OK' if f.question_en else 'EMPTY'}, a_en={'OK' if f.answer_en else 'EMPTY'}")
if empty == 0:
    print("  All filled!")

print()
print("=== Pages ===")
for p in Page.objects.all():
    print(f"  {p.slug}: title_en={'OK' if p.title_en else 'EMPTY'}, hero_title_en={'OK' if p.hero_title_en else 'EMPTY'}, hero_sub_en={'OK' if p.hero_subtitle_en else 'EMPTY'}, body_en={len(p.body_en)}")

print()
print("=== CaseStudy ===")
empty = 0
for c in CaseStudy.objects.all():
    if not c.title_en:
        empty += 1
        print(f"  id={c.id}: title_ru={c.title_ru[:50]} → title_en=EMPTY")
    else:
        print(f"  id={c.id}: title_en={c.title_en[:50]}, task_en={'OK' if c.task_en else 'EMPTY'}, result_en={'OK' if c.result_en else 'EMPTY'}")
if empty == 0:
    print("  All filled!")

print()
print("=== CatalogPDF ===")
empty = 0
for c in CatalogPDF.objects.all():
    if not c.title_en:
        empty += 1
        print(f"  id={c.id}: title_ru={c.title_ru[:60]} → EMPTY")
if empty == 0:
    print(f"  All {CatalogPDF.objects.count()} catalogs have title_en")
else:
    print(f"  {empty} catalogs missing title_en")

print()
print("=== Testimonial ===")
for t in Testimonial.objects.all()[:5]:
    has_en = hasattr(t, 'text_en')
    print(f"  id={t.id} name={t.name}: text_en={'field exists' if has_en else 'NO FIELD'}")

print()
print("=== SiteSettings ===")
s = SiteSettings.load()
print(f"  hero_badge_en={s.hero_badge_en}")
print(f"  hero_cta_text_en={s.hero_cta_text_en}")
