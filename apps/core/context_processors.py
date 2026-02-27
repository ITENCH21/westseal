from .models import SiteSettings, SealCategory
from django.conf import settings


def site_settings(request):
    path = request.path or "/"
    url_name = request.resolver_match.url_name if request.resolver_match else ""

    section_map = [
        ("/products/", "products", "Продукция", "/products/"),
        ("/production/", "production", "Производство", "/production/"),
        ("/catalog/", "catalog", "Каталог", "/catalog/"),
        ("/catalogs/", "catalogs", "Каталоги", "/catalogs/"),
        ("/guide/", "guide", "Справочник", "/guide/"),
        ("/knowledge/", "knowledge", "База знаний", "/knowledge/"),
        ("/contacts/", "contacts", "Контакты", "/contacts/"),
    ]

    current_section = ""
    current_section_label = ""
    current_section_url = ""
    for prefix, key, label, url in section_map:
        if path.startswith(prefix):
            current_section = key
            current_section_label = label
            current_section_url = url
            break

    page_titles = {
        "home": "Главная",
        "about": "О компании",
        "production": "Производство",
        "products": "Продукция",
        "catalogs": "Каталоги PDF",
        "guide": "Примеры подборов",
        "seal_catalog": "Каталог манжет",
        "seal_product": "Карточка товара",
        "knowledge": "База знаний",
        "article_detail": "Статья",
        "contacts": "Контакты",
        "account_login": "Вход",
        "account_register": "Регистрация",
        "account_dashboard": "Личный кабинет",
        "support_requests": "Мои заявки",
        "support_request_create": "Создать заявку",
        "support_request_detail": "Заявка",
        "support_chat": "Чат с поддержкой",
        "privacy": "Политика конфиденциальности",
        "consent": "Согласие на обработку данных",
        "articles": "Статьи",
        "robots": "robots.txt",
    }

    current_page_title = page_titles.get(url_name, "")

    # Top-level categories for global nav ticker (mobile)
    nav_categories = SealCategory.objects.filter(parent__isnull=True).order_by("order", "name")

    return {
        "site_settings": SiteSettings.load(),
        "current_section": current_section,
        "current_section_label": current_section_label,
        "current_section_url": current_section_url,
        "current_page_title": current_page_title,
        "site_url": settings.SITE_URL.rstrip("/"),
        "ga4_id": settings.GA4_ID,
        "yandex_metrika_id": settings.YANDEX_METRIKA_ID,
        "nav_categories": nav_categories,
    }
