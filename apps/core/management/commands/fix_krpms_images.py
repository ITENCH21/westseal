"""
Fix krpms products: remove incorrectly downloaded site logos,
clear image_url and image fields for products using the logo.

Usage:
    python manage.py fix_krpms_images
    python manage.py fix_krpms_images --dry-run
"""
import os

from django.core.management.base import BaseCommand

from apps.core.models import SealProduct


# Logo patterns to detect
LOGO_PATTERNS = [
    "local/templates/",
    "/img/krpms",
    "krpms.webp",
]


def _is_logo_url(url: str) -> bool:
    if not url:
        return False
    return any(p in url for p in LOGO_PATTERNS)


class Command(BaseCommand):
    help = "Remove incorrectly saved logo images from krpms.ru products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print what would be done without making changes",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        prefix = "[DRY RUN] " if dry else ""

        qs = SealProduct.objects.filter(source_url__contains="krpms.ru")
        total = qs.count()
        self.stdout.write(f"Total krpms products: {total}")

        fixed = 0
        for p in qs:
            changed = False

            # Clear image_url if it's a logo
            if _is_logo_url(p.image_url):
                self.stdout.write(f"  {prefix}Clear image_url: {p.name[:50]} ({p.image_url[:80]})")
                if not dry:
                    p.image_url = ""
                changed = True

            # Delete local file if it looks like a logo
            if p.image:
                img_path = p.image.path if hasattr(p.image, 'path') else ""
                img_name = p.image.name or ""
                base = os.path.basename(img_name)
                # Logo file: original name "krpms.webp", or Django-deduplicated "krpms_XXXXX.webp"
                is_logo_file = (
                    _is_logo_url(img_name)
                    or _is_logo_url(img_path)
                    or (base.startswith("krpms") and base.endswith(".webp"))
                )
                if is_logo_file:
                    self.stdout.write(f"  {prefix}Delete image file: {img_name}")
                    if not dry:
                        try:
                            if img_path and os.path.exists(img_path):
                                os.remove(img_path)
                        except OSError as e:
                            self.stdout.write(f"    WARNING: could not delete file: {e}")
                        p.image = ""
                    changed = True

            if changed:
                if not dry:
                    p.save(update_fields=["image_url", "image"])
                fixed += 1

        self.stdout.write(
            f"\n{prefix}Done. Fixed {fixed} of {total} krpms products."
        )
