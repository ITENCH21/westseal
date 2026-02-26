from django.contrib import admin
from .models import (
    SiteSettings,
    Page,
    PageSection,
    CatalogPDF,
    Article,
    FAQItem,
    CaseStudy,
    Testimonial,
    SealCategory,
    SealProduct,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("org_name", "phone", "email", "address")


class PageSectionInline(admin.StackedInline):
    model = PageSection
    extra = 0


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("slug", "template", "title_ru", "is_published", "updated_at")
    list_filter = ("template", "is_published")
    search_fields = ("slug", "title_ru", "title_en")
    inlines = [PageSectionInline]


@admin.register(CatalogPDF)
class CatalogPDFAdmin(admin.ModelAdmin):
    list_display = ("title_ru", "category", "manufacturer", "manufacturer_website", "published_at")
    list_filter = ("category",)
    search_fields = ("title_ru", "title_en", "manufacturer")
    fields = ("title_ru", "title_en", "description_ru", "description_en",
              "category", "manufacturer", "manufacturer_website",
              "file", "cover_image", "published_at")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title_ru", "published_at", "is_published")
    list_filter = ("is_published",)
    search_fields = ("title_ru", "title_en", "summary_ru")


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ("question_ru", "order", "is_published")
    list_filter = ("is_published",)
    search_fields = ("question_ru", "question_en", "answer_ru")
    ordering = ("order", "id")


@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ("title_ru", "lead_time", "order", "is_published")
    list_filter = ("is_published",)
    search_fields = ("title_ru", "title_en", "task_ru", "result_ru")
    ordering = ("order", "id")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "rating", "order", "is_published")
    list_filter = ("is_published", "rating")
    search_fields = ("name", "company", "text_ru", "text_en")
    ordering = ("order", "id")


@admin.register(SealCategory)
class SealCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "parent", "order", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "code", "slug")
    ordering = ("order", "name")


@admin.register(SealProduct)
class SealProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "subcategory", "is_active")
    list_filter = ("is_active", "category", "subcategory")
    search_fields = ("name", "slug", "attributes_text")
    ordering = ("name",)
