from django.db import models
from django.utils import timezone


class SiteSettings(models.Model):
    org_name = models.CharField(max_length=200, default="EURO-SEAL")
    org_legal = models.CharField(max_length=200, default="ИП Туманов Иван Сергеевич")
    org_legal_en = models.CharField(max_length=200, blank=True, default="IE Tumanov Ivan Sergeyevich")
    phone = models.CharField(max_length=50, default="+79626849611")
    email = models.EmailField(default="euro-seal@mail.ru")
    address = models.CharField(max_length=255, default="Арцеуловская аллея 15")
    address_en = models.CharField(max_length=255, blank=True, default="Artseulovsky alley 15")
    work_hours = models.CharField(max_length=120, blank=True, default="Пн–Пт 9:00–18:00 (МСК)")
    hero_badge_ru = models.CharField(max_length=120, blank=True, default="Изготовление и поставка уплотнений")
    hero_badge_en = models.CharField(max_length=120, blank=True, default="Manufacture & supply of seals")
    hero_cta_text_ru = models.CharField(max_length=120, blank=True, default="Отправить заявку")
    hero_cta_text_en = models.CharField(max_length=120, blank=True, default="Send a request")
    hero_cta_url = models.CharField(max_length=200, blank=True, default="/support/requests/new/")
    logo = models.ImageField(upload_to="site/logo/", blank=True, null=True)
    hero_image = models.ImageField(upload_to="site/hero/", blank=True, null=True)

    def __str__(self) -> str:
        return "Site settings"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Page(models.Model):
    TEMPLATE_CHOICES = [
        ("home", "Home"),
        ("about", "About"),
        ("production", "Production"),
        ("products", "Products"),
        ("catalogs", "Catalogs"),
        ("knowledge", "Knowledge"),
        ("contacts", "Contacts"),
        ("custom", "Custom"),
    ]
    slug = models.SlugField(unique=True)
    template = models.CharField(max_length=40, choices=TEMPLATE_CHOICES, default="custom")
    title_ru = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    meta_title_ru = models.CharField(max_length=240, blank=True)
    meta_title_en = models.CharField(max_length=240, blank=True)
    meta_desc_ru = models.CharField(max_length=320, blank=True)
    meta_desc_en = models.CharField(max_length=320, blank=True)
    hero_title_ru = models.CharField(max_length=200, blank=True)
    hero_title_en = models.CharField(max_length=200, blank=True)
    hero_subtitle_ru = models.TextField(blank=True)
    hero_subtitle_en = models.TextField(blank=True)
    body_ru = models.TextField(blank=True)
    body_en = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title_ru or self.slug


class PageSection(models.Model):
    page = models.ForeignKey(Page, related_name="sections", on_delete=models.CASCADE)
    key = models.SlugField(max_length=80)
    title_ru = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    content_ru = models.TextField(blank=True)
    content_en = models.TextField(blank=True)
    image = models.ImageField(upload_to="pages/sections/", blank=True, null=True)
    cta_text_ru = models.CharField(max_length=120, blank=True)
    cta_text_en = models.CharField(max_length=120, blank=True)
    cta_url = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.page.slug}::{self.key}"


class CatalogPDF(models.Model):
    CATEGORY_CHOICES = [
        ("hydraulic", "Hydraulic seals"),
        ("pneumatic", "Pneumatic seals"),
        ("rotary", "Rotary seals"),
        ("oring", "O-rings"),
        ("kits", "Seal kits"),
        ("other", "Other"),
    ]
    title_ru = models.CharField(max_length=220)
    title_en = models.CharField(max_length=220, blank=True)
    description_ru = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="hydraulic")
    manufacturer = models.CharField(max_length=120, blank=True)
    file = models.FileField(upload_to="catalogs/pdfs/")
    cover_image = models.ImageField(upload_to="catalogs/covers/", blank=True, null=True)
    published_at = models.DateField(default=timezone.now)

    class Meta:
        ordering = ["-published_at", "title_ru"]

    def __str__(self) -> str:
        return self.title_ru


class Article(models.Model):
    slug = models.SlugField(unique=True)
    title_ru = models.CharField(max_length=220)
    title_en = models.CharField(max_length=220, blank=True)
    summary_ru = models.TextField(blank=True)
    summary_en = models.TextField(blank=True)
    body_ru = models.TextField(blank=True)
    body_en = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="articles/", blank=True, null=True)
    published_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self) -> str:
        return self.title_ru


class SealCategory(models.Model):
    name = models.CharField(max_length=220)
    name_en = models.CharField(max_length=220, blank=True)
    slug = models.SlugField(unique=True)
    code = models.CharField(max_length=80, blank=True)
    parent = models.ForeignKey("self", related_name="children", on_delete=models.SET_NULL, null=True, blank=True)
    source_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name


class SealProduct(models.Model):
    category = models.ForeignKey(SealCategory, related_name="products", on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey(SealCategory, related_name="sub_products", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=260)
    name_en = models.CharField(max_length=260, blank=True)
    slug = models.SlugField(unique=True)
    source_url = models.URLField(unique=True)
    image = models.ImageField(upload_to="catalog/products/", blank=True, null=True)
    image_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    attributes = models.JSONField(default=list, blank=True)
    attributes_text = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

class FAQItem(models.Model):
    question_ru = models.CharField(max_length=260)
    question_en = models.CharField(max_length=260, blank=True)
    answer_ru = models.TextField()
    answer_en = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.question_ru


class CaseStudy(models.Model):
    title_ru = models.CharField(max_length=220)
    title_en = models.CharField(max_length=220, blank=True)
    task_ru = models.TextField(blank=True)
    task_en = models.TextField(blank=True)
    result_ru = models.TextField(blank=True)
    result_en = models.TextField(blank=True)
    lead_time = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to="cases/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title_ru


class Testimonial(models.Model):
    name = models.CharField(max_length=140)
    company = models.CharField(max_length=200, blank=True)
    text_ru = models.TextField()
    text_en = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(default=5)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name
