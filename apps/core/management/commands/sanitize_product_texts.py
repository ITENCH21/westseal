"""
Sanitize product descriptions and attributes:
- Remove phone numbers
- Remove email addresses
- Remove URLs to source sites
- Remove company name mentions (КРПМС, seal-tech.ru, mkt-rti.ru, quers.ru, krpms.ru, etc.)

Usage:
    python manage.py sanitize_product_texts
    python manage.py sanitize_product_texts --dry-run
"""
import re

from django.core.management.base import BaseCommand

from apps.core.models import SealProduct

# Patterns to remove
# Russian phone numbers: +7 (xxx) xxx-xx-xx or 8-800-xxx-xx-xx style
PHONE_RE = re.compile(
    r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{2}[\s\-]\d{2}'
    r'|(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{4}'
    r'|(?:\+7|8)\s*\(\d{3}\)\s*\d{3}[- ]\d{2}[- ]\d{2}',
)
EMAIL_RE = re.compile(
    r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}',
)
URL_RE = re.compile(
    r'https?://[^\s\)\]\>\"\']+',
    re.IGNORECASE,
)
DOMAIN_RE = re.compile(
    r'\b(?:www\.)?(?:krpms|mkt-rti|seal-tech|quers|mkt\.rti)\.[a-z.]+\b',
    re.IGNORECASE,
)
# Company names to remove
COMPANY_NAMES = [
    r'ООО\s+ПТК\s+[«"]КРПМС[»"]',
    r'ООО\s+[«"]КРПМС[»"]',
    r'компани[ияей]+\s+КРПМС',
    r'КРПМС',
    r'Seal-TECH',
    r'ООО\s+[«"]СИЛ-ТЕК[»"]',
    r'СИЛ-ТЕК',
    r'mkt-rti\.ru',
    r'quers\.ru',
]
COMPANY_RE = re.compile(
    '|'.join(f'(?:{p})' for p in COMPANY_NAMES),
    re.IGNORECASE,
)


def _clean(text: str) -> tuple[str, int]:
    """Return (cleaned_text, number_of_changes)."""
    if not text:
        return text, 0
    original = text
    text = URL_RE.sub('', text)
    text = EMAIL_RE.sub('', text)
    text = PHONE_RE.sub('', text)
    text = DOMAIN_RE.sub('', text)
    text = COMPANY_RE.sub('', text)
    # Clean up double spaces and lines
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    changes = int(original != text)
    return text, changes


class Command(BaseCommand):
    help = "Remove phone numbers, emails, URLs and source site mentions from product texts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would change without saving",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        prefix = "[DRY RUN] " if dry else ""

        total = SealProduct.objects.count()
        self.stdout.write(f"Scanning {total} products...")

        changed_count = 0
        for p in SealProduct.objects.all():
            update_fields = []

            new_desc, d = _clean(p.description)
            if d:
                self.stdout.write(f"  {prefix}description changed: {p.name[:50]}")
                if not dry:
                    p.description = new_desc
                    update_fields.append("description")

            new_attrs_text, d2 = _clean(p.attributes_text)
            if d2:
                if not dry:
                    p.attributes_text = new_attrs_text
                    update_fields.append("attributes_text")

            # Clean inside attributes JSON
            if p.attributes:
                new_attrs = []
                attrs_changed = False
                for attr in p.attributes:
                    nv, d3 = _clean(str(attr.get("value", "")))
                    nn, d4 = _clean(str(attr.get("name", "")))
                    if d3 or d4:
                        attrs_changed = True
                    new_attrs.append({"name": nn, "value": nv})
                if attrs_changed:
                    if not dry:
                        p.attributes = new_attrs
                        update_fields.append("attributes")

            if update_fields:
                if not dry:
                    p.save(update_fields=update_fields)
                changed_count += 1

        self.stdout.write(
            f"\n{prefix}Done. {changed_count} products had text changes."
        )
