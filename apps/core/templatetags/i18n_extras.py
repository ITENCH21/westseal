from django import template
from django.utils import translation

register = template.Library()


@register.filter
def tr(obj, field_base: str):
    if not obj:
        return ""
    lang = translation.get_language() or "ru"
    suffix = "_ru" if lang.startswith("ru") else "_en"
    return getattr(obj, f"{field_base}{suffix}", "")
