from django import template
import os

register = template.Library()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov"}


@register.filter
def file_ext(path: str) -> str:
    _, ext = os.path.splitext(path or "")
    return ext.lower()


@register.filter
def is_image(path: str) -> bool:
    return file_ext(path) in IMAGE_EXTS


@register.filter
def is_video(path: str) -> bool:
    return file_ext(path) in VIDEO_EXTS
