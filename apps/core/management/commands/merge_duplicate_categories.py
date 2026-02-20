"""
Merge duplicate seal categories from different import sources into canonical ones.

Plan:
  grjazesemniki          ← krpms-gryazesemniki, quers-a-seals
  napravljajuwie_gidrocilindrov ← krpms-napravlyayushhie-kolca-dlya-gidrocilindrov, quers-f-seals
  uplotnenija_porshnja   ← krpms-uplotneniya-porshnya, quers-k-seals
  uplotnenija_shtoka     ← krpms-uplotneniya-shtoka, quers-s-seals
  kolca_uplatnitelnye    ← krpms-kruglogo-secheniya, quers-seals-rings
  pnevmaticheskoe_uplotnenija ← krpms-pnevmaticheskie-uplotneniya-shtoka
  krpms-rotornye-uplotneniya  ← quers-r-seals
  krpms-opornye-koltsa        ← quers-st-seals

Usage:
    python manage.py merge_duplicate_categories
    python manage.py merge_duplicate_categories --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import SealCategory, SealProduct


# target slug → list of source slugs to absorb
MERGE_PLAN = [
    ("grjazesemniki", ["krpms-gryazesemniki", "quers-a-seals"]),
    ("napravljajuwie_gidrocilindrov", [
        "krpms-napravlyayushhie-kolca-dlya-gidrocilindrov",
        "quers-f-seals",
    ]),
    ("uplotnenija_porshnja", ["krpms-uplotneniya-porshnya", "quers-k-seals"]),
    ("uplotnenija_shtoka", ["krpms-uplotneniya-shtoka", "quers-s-seals"]),
    ("kolca_uplatnitelnye", ["krpms-kruglogo-secheniya", "quers-seals-rings"]),
    ("pnevmaticheskoe_uplotnenija", ["krpms-pnevmaticheskie-uplotneniya-shtoka"]),
    ("krpms-rotornye-uplotneniya", ["quers-r-seals"]),
    ("krpms-opornye-koltsa", ["quers-st-seals"]),
]


class Command(BaseCommand):
    help = "Merge duplicate categories from multiple import sources into one canonical category."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        if dry:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved.\n"))

        total_moved = 0

        for target_slug, source_slugs in MERGE_PLAN:
            target = SealCategory.objects.filter(slug=target_slug).first()
            if not target:
                self.stdout.write(self.style.WARNING(
                    f"  SKIP: target category not found: {target_slug!r}"
                ))
                continue

            for src_slug in source_slugs:
                src = SealCategory.objects.filter(slug=src_slug).first()
                if not src:
                    self.stdout.write(f"  SKIP: source not found: {src_slug!r}")
                    continue

                by_cat = SealProduct.objects.filter(category=src)
                by_sub = SealProduct.objects.filter(subcategory=src)
                n_cat = by_cat.count()
                n_sub = by_sub.count()
                children = SealCategory.objects.filter(parent=src)
                n_children = children.count()

                self.stdout.write(
                    "  MERGE %r [%s] → %r [%s] | %d products, %d subcategory refs, %d children" % (
                        src.name, src_slug, target.name, target_slug,
                        n_cat, n_sub, n_children,
                    )
                )

                if not dry:
                    with transaction.atomic():
                        by_cat.update(category=target)
                        by_sub.update(subcategory=target)
                        children.update(parent=target)
                        src.is_active = False
                        src.save(update_fields=["is_active"])

                total_moved += n_cat + n_sub

        if dry:
            self.stdout.write(self.style.SUCCESS(
                "\nDry run complete. Would move ~%d product refs." % total_moved
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "\nDone. Moved %d product refs. Deactivated source categories." % total_moved
            ))
