from django.urls import path
from . import views

urlpatterns = [
    path("robots.txt", views.robots_view, name="robots"),
    path("sitemap.xml", views.sitemap_view, name="sitemap"),
    path("", views.home, name="home"),
    path("about/", views.page_about, name="about"),
    path("production/", views.page_production, name="production"),
    path("products/", views.page_products, name="products"),
    path("catalogs/", views.catalogs, name="catalogs"),
    path("catalog/", views.seal_catalog, name="seal_catalog"),
    path("catalog/item/<slug:slug>/", views.seal_product, name="seal_product"),
    path("catalog/import-status/", views.catalog_import_status, name="catalog_import_status"),
    path("catalog/suggest/", views.catalog_search_suggest, name="catalog_search_suggest"),
    path("guide/", views.guide, name="guide"),
    path("knowledge/", views.articles, name="knowledge"),
    path("knowledge/<slug:slug>/", views.article_detail, name="article_detail"),
    path("contacts/", views.contacts, name="contacts"),
    path("privacy/", views.page_privacy, name="privacy"),
    path("consent/", views.page_consent, name="consent"),
]
