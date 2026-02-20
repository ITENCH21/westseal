"""
Удаляет мусорные продукты:
- "Каталог изделий" / "Каталог продукции" — обзорные страницы конкурентов
- Продукты с логотипами чужих брендов в image или image_url
"""
import os
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.core.models import SealProduct


JUNK_NAMES = [
    "каталог изделий",
    "каталог продукции",
    "каталог товаров",
]

JUNK_NAME_STARTS = [
    "Каталог",  # Каталог изделий, Каталог продукции и т.д.
]

LOGO_PATTERNS_IMAGE = [
    "logotip",
    "logotype",
    "_logo",
    "-logo",
    "/logo",
    "mkt_logo",
    "mkt-logo",
    "c18e7f59936984791517f82f2440e8ec",  # МКТ логотип
]

LOGO_PATTERNS_URL = [
    "logotip",
    "logotype",
    "/logo.",
    "_logo.",
]


class Command(BaseCommand):
    help = "Удаляет мусорные продукты (обзорные страницы, логотипы конкурентов)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать, не удалять")

    def handle(self, *args, **options):
        dry = options["dry_run"]

        # 1. Мусорные по имени (точное совпадение icontains)
        name_q = Q()
        for n in JUNK_NAMES:
            name_q |= Q(name__icontains=n)
        # 1b. По началу имени (Каталог ...)
        for s in JUNK_NAME_STARTS:
            name_q |= Q(name__istartswith=s)

        # 2. Мусорные по логотипу в поле image
        img_q = Q()
        for p in LOGO_PATTERNS_IMAGE:
            img_q |= Q(image__icontains=p)

        # 3. Мусорные по логотипу в поле image_url (не медиа)
        url_q = Q()
        for p in LOGO_PATTERNS_URL:
            url_q |= Q(image_url__icontains=p)

        qs = SealProduct.objects.filter(name_q | img_q | url_q)
        total = qs.count()
        self.stdout.write(f"Найдено мусорных продуктов: {total}")

        for p in qs[:50]:
            self.stdout.write(f"  [{p.id}] {p.name[:60]} | img={str(p.image)[:50]}")

        if total > 50:
            self.stdout.write(f"  ... и ещё {total - 50}")

        if not dry and total > 0:
            # Разделяем: "Каталог *" — удаляем полностью, остальные — только чистим image
            from django.db.models import Q as _Q
            junk_name_q = _Q()
            for n in JUNK_NAMES:
                junk_name_q |= _Q(name__icontains=n)
            for s in JUNK_NAME_STARTS:
                junk_name_q |= _Q(name__istartswith=s)

            to_delete = qs.filter(junk_name_q)
            to_clear_image = qs.exclude(junk_name_q)

            # Удаляем каталожные заглушки (полностью)
            deleted_files = 0
            for p in to_delete:
                if p.image:
                    try:
                        path = p.image.path
                        if os.path.isfile(path):
                            os.remove(path)
                            deleted_files += 1
                    except Exception:
                        pass
            deleted_count, _ = to_delete.delete()
            self.stdout.write(self.style.SUCCESS(f"Удалено мусорных страниц: {deleted_count}, файлов: {deleted_files}"))

            # Очищаем только изображение у реальных товаров с логотипом
            cleared = 0
            for p in to_clear_image:
                if p.image:
                    try:
                        path = p.image.path
                        if os.path.isfile(path):
                            os.remove(path)
                    except Exception:
                        pass
                    p.image = None
                if p.image_url:
                    p.image_url = ""
                p.save(update_fields=["image", "image_url"])
                cleared += 1
            if cleared:
                self.stdout.write(self.style.SUCCESS(f"Очищено изображений у реальных товаров: {cleared}"))
        elif dry:
            self.stdout.write("(dry-run, ничего не удалено)")
