from django.core.management.base import BaseCommand
from apps.core.models import SealCategory, SealProduct


class Command(BaseCommand):
    help = "Fix krpms category structure: promote level-2 to top-level, hide empties."

    def handle(self, *args, **options):
        root = SealCategory.objects.filter(slug='krpms-uplotneniya').first()
        if root:
            level2 = list(SealCategory.objects.filter(parent=root))
            self.stdout.write(f'Promoting {len(level2)} categories to top-level...')
            for cat in level2:
                cat.parent = None
                cat.save(update_fields=['parent'])
                cnt = SealProduct.objects.filter(category=cat).count()
                self.stdout.write(f'  {cat.slug}  ({cnt} products)')
            root.is_active = False
            root.save(update_fields=['is_active'])
            self.stdout.write('Root krpms-uplotneniya deactivated.')
        else:
            self.stdout.write('Root krpms-uplotneniya not found (already fixed?).')

        # Скрываем пустые top-level krpms-категории
        hidden = 0
        for cat in SealCategory.objects.filter(slug__startswith='krpms-', parent__isnull=True, is_active=True):
            total = (
                SealProduct.objects.filter(category=cat).count() +
                SealProduct.objects.filter(subcategory__parent=cat).count()
            )
            if total == 0:
                cat.is_active = False
                cat.save(update_fields=['is_active'])
                self.stdout.write(f'  Hidden empty: {cat.slug}')
                hidden += 1
        self.stdout.write(f'Hidden {hidden} empty categories.')

        active = SealCategory.objects.filter(slug__startswith='krpms-', parent__isnull=True, is_active=True)
        self.stdout.write(f'\nActive top-level krpms categories: {active.count()}')
        for c in active.order_by('name'):
            cnt = SealProduct.objects.filter(category=c).count()
            self.stdout.write(f'  {c.slug}: {cnt} products')
