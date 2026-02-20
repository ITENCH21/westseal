"""
Удаляет логотип Seal-TECH (logotip-3_*.svg) из продуктов.
Поле image очищается, файл удаляется с диска.

Usage:
    python manage.py fix_sealtech_images
    python manage.py fix_sealtech_images --dry-run
"""
import os

from django.core.management.base import BaseCommand
from apps.core.models import SealProduct

LOGO_PATTERNS = ["logotip-3", "logotip_3", "logotip3", "seal-tech-logo"]


def _is_logo(name: str) -> bool:
    if not name:
        return False
    n = name.lower()
    return any(p in n for p in LOGO_PATTERNS)


class Command(BaseCommand):
    help = "Remove Seal-TECH logo images from products."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Print what would be done without changes")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        prefix = "[DRY RUN] " if dry else ""

        qs = SealProduct.objects.filter(source_url__icontains="seal-tech.ru")
        self.stdout.write(f"Seal-TECH products total: {qs.count()}")

        fixed = 0
        deleted_files = 0
        for p in qs:
            changed = False

            if p.image_url and _is_logo(p.image_url):
                self.stdout.write(f"  {prefix}Clear image_url: {p.image_url[:80]}")
                if not dry:
                    p.image_url = ""
                changed = True

            if p.image:
                img_name = p.image.name or ""
                img_path = ""
                try:
                    img_path = p.image.path
                except Exception:
                    pass
                if _is_logo(img_name) or _is_logo(os.path.basename(img_name)):
                    self.stdout.write(f"  {prefix}Delete image: {img_name}")
                    if not dry:
                        try:
                            if img_path and os.path.exists(img_path):
                                os.remove(img_path)
                                deleted_files += 1
                        except OSError as e:
                            self.stdout.write(f"    WARNING: {e}")
                        p.image = ""
                    changed = True

            if changed:
                fixed += 1
                if not dry:
                    p.save(update_fields=["image", "image_url"])

        self.stdout.write(
            f"\n{prefix}Done. Products fixed: {fixed}, files deleted: {deleted_files}"
        )
