from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.utils import timezone
from xml.sax.saxutils import escape
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.urls import reverse
from django.conf import settings
from types import SimpleNamespace
from collections import deque
import os
import re
from .models import (
    Page,
    CatalogPDF,
    Article,
    FAQItem,
    CaseStudy,
    Testimonial,
    SealCategory,
    SealProduct,
)
from apps.support.forms import QuickLeadForm
from .search import seal_product_search


def _get_or_create_page(slug: str, template: str, title_ru: str, title_en: str):
    page, _ = Page.objects.get_or_create(
        slug=slug,
        defaults={
            "template": template,
            "title_ru": title_ru,
            "title_en": title_en,
            "hero_title_ru": title_ru,
            "hero_title_en": title_en,
        },
    )
    return page


def home(request):
    page = _get_or_create_page("home", "home", "Гидравлические и пневматические уплотнения", "Hydraulic & pneumatic seals")
    faq_items = FAQItem.objects.filter(is_published=True)[:8]
    case_studies = CaseStudy.objects.filter(is_published=True)[:6]
    testimonials = Testimonial.objects.filter(is_published=True)[:6]
    catalog_count = SealProduct.objects.filter(is_active=True).count()
    return render(
        request,
        "core/home.html",
        {
            "page": page,
            "quick_lead_form": QuickLeadForm(),
            "faq_items": faq_items,
            "case_studies": case_studies,
            "testimonials": testimonials,
            "catalog_count": catalog_count,
        },
    )


def page_about(request):
    page = _get_or_create_page("about", "about", "О компании", "About WESTSEAL")
    return render(request, "core/about.html", {"page": page})


def page_production(request):
    page = _get_or_create_page("production", "production", "Производство и материалы", "Manufacturing & materials")
    return render(request, "core/production.html", {"page": page})


def page_products(request):
    page = _get_or_create_page("products", "products", "Продукция", "Products")
    return render(request, "core/products.html", {"page": page})


def page_privacy(request):
    return render(request, "core/privacy.html", {"page": None})


def page_consent(request):
    return render(request, "core/consent.html", {"page": None})


def catalogs(request):
    page = _get_or_create_page("catalogs", "catalogs", "Каталоги PDF", "PDF catalogs")
    catalogs = CatalogPDF.objects.all()
    return render(request, "core/catalogs.html", {"page": page, "catalogs": catalogs})


def articles(request):
    page = _get_or_create_page("knowledge", "knowledge", "База знаний", "Knowledge base")
    articles = Article.objects.filter(is_published=True)
    return render(request, "core/articles.html", {"page": page, "articles": articles})


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    return render(request, "core/article_detail.html", {"article": article, "page": article})


def contacts(request):
    page = _get_or_create_page("contacts", "contacts", "Контакты", "Contacts")
    return render(request, "core/contacts.html", {"page": page})


def seal_catalog(request):
    page = _get_or_create_page("catalog", "custom", "Каталог манжет", "Seal catalog")
    q = (request.GET.get("q") or "").strip()
    category_slug = request.GET.get("category") or ""
    sub_slug = request.GET.get("sub") or ""
    page_number = request.GET.get("page") or "1"
    show_import_panel = bool(getattr(request.user, "is_staff", False)) or (request.GET.get("debug") == "1")

    categories = (
        SealCategory.objects.filter(parent__isnull=True, is_active=True)
        .annotate(product_count=Count("products", filter=Q(products__is_active=True), distinct=True))
        .annotate(child_count=Count("children", filter=Q(children__is_active=True), distinct=True))
        .filter(product_count__gt=0)
    )
    category = categories.filter(slug=category_slug).first() if category_slug else None
    subcategories = (
        SealCategory.objects.filter(parent=category, is_active=True)
        .annotate(product_count=Count("sub_products", filter=Q(sub_products__is_active=True), distinct=True))
        .filter(product_count__gt=0)
        .order_by("-product_count", "code")
        if category
        else SealCategory.objects.none()
    )
    subcategory = subcategories.filter(slug=sub_slug).first() if sub_slug else None

    view_mode = "products"
    if not q and not category:
        view_mode = "categories"

    products = SealProduct.objects.none()
    paginator = None
    page_obj = None
    base_qs = ""
    page_numbers = []

    def _short_attr_name(name: str) -> str:
        label = (name or "").strip()
        label = re.sub(r"\s*\(.*?\)\s*", "", label)
        # Сокращаем длинные русские имена
        label = label.replace("Стандартный материал", "Материал")
        label = label.replace("Код уплотнения", "Профиль")
        label = label.replace("Скорость скольжения", "Скорость")
        label = label.replace("Внутренний", "Внутр.")
        label = label.replace("Внешний", "Внеш.")
        label = label.replace("Диаметр", "диам.")
        label = label.replace("Ширина", "шир.")
        label = label.replace("Толщина", "толщ.")
        label = label.replace("Высота", "выс.")
        label = re.sub(r"\s+", " ", label).strip()
        if len(label) > 20:
            label = label[:19].rstrip() + "…"
        return label

    if view_mode != "categories":
        products = SealProduct.objects.filter(is_active=True)
        if category:
            products = products.filter(category=category)
        if subcategory:
            products = products.filter(subcategory=subcategory)
        if q:
            products = seal_product_search(products, q)

        paginator = Paginator(products, 24)
        page_obj = paginator.get_page(page_number)

        for item in page_obj.object_list:
            specs = []
            if not item.attributes and item.name:
                m = re.search(r"(\d+(?:[.,]\d+)?\s*[x×хХ]\s*\d+(?:[.,]\d+)?(?:\s*[x×хХ]\s*\d+(?:[.,]\d+)?)?)", item.name)
                if m:
                    specs.append({"name": _("Размер"), "value": m.group(1).replace("×", "x").replace("х", "x").replace("Х", "x")})
            if item.attributes:
                priority = ("профиль", "код уплотн", "материал", "d1", "d2", "h", "внутр", "внеш", "выс", "толщ", "шир", "давлен")
                attrs = list(item.attributes or [])
                attrs.sort(
                    key=lambda a: min(
                        [priority.index(p) for p in priority if p in (a.get("name", "").lower())] or [999]
                    )
                )
                for attr in attrs:
                    if len(specs) >= 3:
                        break
                    raw_name = attr.get("name", "")
                    v = (attr.get("value") or "").strip()
                    if not raw_name or not v:
                        continue
                    # Производитель заменяем на WESTSEAL
                    if "производ" in raw_name.lower():
                        specs.append({"name": "Производитель", "value": "WESTSEAL"})
                        continue
                    n = _short_attr_name(raw_name)
                    if len(v) > 38:
                        v = v[:37].rstrip() + "…"
                    specs.append({"name": n, "value": v})
            setattr(item, "display_specs", specs)

        qs = request.GET.copy()
        qs.pop("page", None)
        base_qs = qs.urlencode()
        current = page_obj.number
        total_pages = page_obj.paginator.num_pages
        page_numbers = sorted(
            set([1, total_pages] + list(range(max(1, current - 2), min(total_pages, current + 2) + 1)))
        )

    return render(
        request,
        "core/catalog.html",
        {
            "page": page,
            "view_mode": view_mode,
            "show_import_panel": show_import_panel,
            "categories": categories,
            "category": category,
            "subcategories": subcategories,
            "subcategory": subcategory,
            "products": (page_obj.object_list if page_obj else []),
            "page_obj": page_obj,
            "paginator": paginator,
            "base_qs": base_qs,
            "page_numbers": page_numbers,
            "q": q,
            # SEO overrides
            "seo_title": (
                f"{subcategory.name} — {category.name}" if subcategory
                else f"{category.name} — каталог уплотнений" if category
                else None
            ),
            "seo_desc": (
                f"Каталог уплотнений WESTSEAL — {subcategory.name}. "
                f"Подбор и заказ уплотнений {subcategory.name.lower()} по техническим характеристикам." if subcategory
                else f"Каталог уплотнений WESTSEAL — {category.name}. "
                f"Гидравлические уплотнения {category.name.lower()}: характеристики, подбор, заказ." if category
                else None
            ),
        },
    )


def seal_product(request, slug):
    product = get_object_or_404(SealProduct, slug=slug, is_active=True)

    # Build SEO meta description from attributes + description
    attrs = product.attributes or []
    # Key specs for meta: exclude empty values, prefer named attributes
    priority_keys = ("Код уплотнения", "Производитель", "Стандартный материал",
                     "Температура", "Давление", "Материал")
    spec_parts = []
    _BRANDS_REPLACE = {"krpms", "kastas", "aston seals", "aston", "seal-tech", "sealtech", "mkt", "mkt-rti", "quers"}
    attr_dict = {}
    for a in attrs:
        if not a.get("value"):
            continue
        k, v = a["name"], a["value"]
        if "производ" in k.lower() and v.lower().strip() in _BRANDS_REPLACE:
            v = "WESTSEAL"
        attr_dict[k] = v
    for key in priority_keys:
        if key in attr_dict:
            spec_parts.append(f"{key}: {attr_dict[key]}")
    if not spec_parts:
        for a in attrs[:4]:
            if a.get("value"):
                spec_parts.append(f"{a['name']}: {a['value']}")

    cat_name = product.category.name if product.category else ""

    # Фильтрация мусорных описаний (скрапинг-артефакты)
    _JUNK_PHRASES = (
        "отправить резюме",
        "прикрепить файл",
        "обработки персональных данных",
        "нажимая на кнопку",
        "политики конфиденциальности",
    )
    clean_description = product.description or ""
    if clean_description and any(p in clean_description.lower() for p in _JUNK_PHRASES):
        clean_description = ""

    if spec_parts:
        meta_desc = f"{product.name} — {cat_name}. {', '.join(spec_parts)}. Купить уплотнение в WESTSEAL."
    elif clean_description:
        meta_desc = f"{product.name} — {cat_name}. {clean_description[:180]}"
    else:
        meta_desc = f"{product.name} — {cat_name}. Технические характеристики и заказ в WESTSEAL."
    meta_desc = meta_desc[:300]

    meta_title = f"{product.name} — купить, характеристики"
    if cat_name:
        meta_title = f"{product.name} | {cat_name} | WESTSEAL"

    page = SimpleNamespace(
        title_ru=product.name,
        meta_title_ru=meta_title,
        meta_desc_ru=meta_desc,
    )
    back_url = "/catalog/"
    if product.category:
        back_url = f"/catalog/?category={product.category.slug}"
        if product.subcategory:
            back_url += f"&sub={product.subcategory.slug}"

    # Brand for structured data — всегда WESTSEAL
    brand_name = "WESTSEAL"

    # Очищенный список атрибутов — заменяем чужой бренд на WESTSEAL
    _THIRD_PARTY_BRANDS = {"krpms", "kastas", "aston seals", "aston", "seal-tech", "sealtech", "mkt", "mkt-rti", "quers"}
    display_attrs = []
    for a in attrs:
        name = a.get("name", "")
        value = a.get("value", "")
        if "производ" in name.lower() and (value or "").lower().strip() in _THIRD_PARTY_BRANDS:
            display_attrs.append({"name": name, "value": "WESTSEAL"})
        else:
            display_attrs.append(a)

    return render(
        request,
        "core/catalog_detail.html",
        {
            "product": product,
            "display_attrs": display_attrs,
            "clean_description": clean_description,
            "page": page,
            "back_url": back_url,
            "brand_name": brand_name,
            "spec_parts": spec_parts,
        },
    )


def catalog_import_status(request):
    q = (request.GET.get("q") or "").strip()
    category_slug = request.GET.get("category") or ""
    sub_slug = request.GET.get("sub") or ""

    category = (
        SealCategory.objects.filter(parent__isnull=True, slug=category_slug, is_active=True).first()
        if category_slug
        else None
    )
    subcategory = (
        SealCategory.objects.filter(parent=category, slug=sub_slug, is_active=True).first()
        if sub_slug and category
        else None
    )

    products = SealProduct.objects.filter(is_active=True)
    if category:
        products = products.filter(category=category)
    if subcategory:
        products = products.filter(subcategory=subcategory)
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(attributes_text__icontains=q)
        )

    latest_items = []
    for item in products.order_by("-created_at")[:8]:
        image_url = item.image.url if item.image else ""
        latest_items.append(
            {
                "name": item.name,
                "url": reverse("seal_product", args=[item.slug]),
                "image": image_url or "",
            }
        )

    log_path = os.path.join(settings.BASE_DIR, "data", "import_mkt_rti.log")
    log_tail = []
    running = False
    updated_at = None
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as log_fp:
                log_tail = list(deque(log_fp, maxlen=8))
        except OSError:
            log_tail = []
        try:
            mtime = os.path.getmtime(log_path)
            updated_at = timezone.datetime.fromtimestamp(mtime).isoformat()
            running = (timezone.now().timestamp() - mtime) < 120
        except OSError:
            running = False

    payload = {
        "running": running,
        "total": SealProduct.objects.filter(is_active=True).count(),
        "filtered_total": products.count(),
        "latest": latest_items,
        "log": [line.rstrip("\n") for line in log_tail if line.strip()],
        "updated_at": updated_at,
    }
    return JsonResponse(payload)


def catalog_search_suggest(request):
    """Returns up to 10 product name suggestions for autocomplete."""
    q = (request.GET.get("q") or "").strip()
    category_slug = request.GET.get("category") or ""
    if len(q) < 2:
        return JsonResponse({"suggestions": []})

    products = SealProduct.objects.filter(is_active=True)
    if category_slug:
        cat = SealCategory.objects.filter(slug=category_slug, is_active=True).first()
        if cat:
            products = products.filter(category=cat)

    # Exact prefix match first, then contains
    prefix_qs = products.filter(name__istartswith=q).values_list("name", flat=True).order_by("name")[:6]
    contains_qs = products.filter(name__icontains=q).exclude(name__istartswith=q).values_list("name", flat=True).order_by("name")[:6]

    seen = set()
    suggestions = []
    for name in list(prefix_qs) + list(contains_qs):
        if name not in seen:
            seen.add(name)
            suggestions.append(name)
        if len(suggestions) >= 10:
            break

    return JsonResponse({"suggestions": suggestions})


def robots_view(request):
    content = "User-agent: *\nDisallow:\nSitemap: " + request.build_absolute_uri("/sitemap.xml")
    return HttpResponse(content, content_type="text/plain")


def sitemap_view(request):
    static_urls = [
        ("/", "1.0"),
        ("/about/", "0.8"),
        ("/production/", "0.9"),
        ("/products/", "0.9"),
        ("/catalog/", "0.9"),
        ("/catalogs/", "0.9"),
        ("/knowledge/", "0.9"),
        ("/contacts/", "0.8"),
    ]
    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, priority in static_urls:
        loc = escape(request.build_absolute_uri(path))
        body.append(f"  <url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>{priority}</priority></url>")
    # Category pages (top-level and subcategory)
    for cat in SealCategory.objects.filter(is_active=True).only("slug", "parent_id").order_by("parent_id", "slug"):
        if cat.parent_id:
            url_path = f"/catalog/?subcat={cat.slug}"
        else:
            url_path = f"/catalog/?cat={cat.slug}"
        loc = escape(request.build_absolute_uri(url_path))
        body.append(f"  <url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>")
    # Articles
    for article in Article.objects.filter(is_published=True).only("slug", "published_at"):
        loc = escape(request.build_absolute_uri(f"/knowledge/{article.slug}/"))
        lastmod = article.published_at.date().isoformat() if article.published_at else ""
        body.append(f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>")
    # All active products (no limit — ~25k products, well within 50k sitemap limit)
    for product in SealProduct.objects.filter(is_active=True).only("slug", "updated_at").order_by("slug"):
        loc = escape(request.build_absolute_uri(f"/catalog/item/{product.slug}/"))
        lastmod = product.updated_at.date().isoformat()
        body.append(f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>")
    body.append("</urlset>")
    body = "\n".join(body)
    return HttpResponse(body, content_type="application/xml")
