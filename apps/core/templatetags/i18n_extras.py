from django import template
from django.utils import translation

register = template.Library()


@register.filter
def tr(obj, field_base: str):
    if not obj:
        return ""
    lang = translation.get_language() or "ru"
    suffix = "_ru" if lang.startswith("ru") else "_en"
    # Try language-specific field first (e.g. name_ru / name_en)
    value = getattr(obj, f"{field_base}{suffix}", None)
    if isinstance(value, str) and value:
        return value
    # Fall back to base field (e.g. 'name') — covers models without _ru/_en
    fallback = getattr(obj, field_base, "")
    # Guard: Python strings have built-in methods (.title, .name etc.) — skip callables
    return fallback if isinstance(fallback, str) else ""
