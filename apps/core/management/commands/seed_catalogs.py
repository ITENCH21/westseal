import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files import File
from django.utils import timezone
from apps.core.models import CatalogPDF


class Command(BaseCommand):
    help = "Seed CatalogPDF items from data/catalogs/sources.json"

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parents[4]
        sources_path = base_dir / "data" / "catalogs" / "sources.json"
        if not sources_path.exists():
            self.stdout.write(self.style.ERROR("sources.json not found"))
            return
        data = json.loads(sources_path.read_text(encoding="utf-8"))
        created = 0
        for item in data:
            local_path = item.get("local_path")
            if not local_path:
                continue
            file_path = base_dir / local_path
            if not file_path.exists():
                continue
            cover_path = None
            cover_rel = item.get("cover_svg")
            if cover_rel:
                cover_path = base_dir / cover_rel
            title_ru = item.get("title_ru") or file_path.stem
            obj, is_new = CatalogPDF.objects.get_or_create(
                title_ru=title_ru,
                defaults={
                    "title_en": item.get("title_en", ""),
                    "description_ru": item.get("description_ru", ""),
                    "description_en": item.get("description_en", ""),
                    "category": item.get("category", "other"),
                    "manufacturer": item.get("manufacturer", ""),
                    "published_at": timezone.now().date(),
                },
            )
            if is_new:
                with open(file_path, "rb") as f:
                    obj.file.save(file_path.name, File(f), save=True)
                created += 1
            if cover_path and cover_path.exists() and not obj.cover_image:
                with open(cover_path, "rb") as f:
                    obj.cover_image.save(cover_path.name, File(f), save=True)
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} catalogs"))
