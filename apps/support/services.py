import json
import urllib.request
import urllib.parse
from django.conf import settings
from django.core.mail import send_mail


# ─── helpers ───────────────────────────────────────────────────────────────

def _notification_recipient() -> str:
    default_email = getattr(settings, "DEFAULT_TO_EMAIL", "") or ""
    if default_email:
        return default_email
    try:
        from apps.core.models import SiteSettings
        return SiteSettings.load().email
    except Exception:
        return ""


def _admin_chat_id() -> str:
    return getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", "") or ""


# ─── email fallback ─────────────────────────────────────────────────────────

def send_admin_notification(subject: str, body: str) -> bool:
    to_email = _notification_recipient()
    if not to_email:
        return False
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@euro-seal.local")
    try:
        sent = send_mail(
            subject=subject[:160],
            message=body,
            from_email=from_email,
            recipient_list=[to_email],
            fail_silently=True,
        )
        return sent > 0
    except Exception:
        return False


# ─── telegram core ───────────────────────────────────────────────────────────

def send_telegram_message(chat_id: str, text: str, parse_mode: str = "HTML",
                          reply_to_message_id: int | None = None) -> "dict | bool":
    """Отправляет сообщение в Telegram.
    Возвращает полный JSON-ответ API (dict) при успехе или False при ошибке.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params: dict = {"chat_id": chat_id, "text": text[:4096], "parse_mode": parse_mode}
    if reply_to_message_id:
        params["reply_to_message_id"] = reply_to_message_id
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return False


def _tg_message_id(result: "dict | bool") -> "int | None":
    """Извлекает message_id из ответа send_telegram_message."""
    if isinstance(result, dict) and result.get("ok"):
        return result.get("result", {}).get("message_id")
    return None


def parse_telegram_update(payload: dict) -> "dict | None":
    """Парсит входящий Telegram update.
    Добавляет reply_to_message_id если сообщение является ответом.
    """
    message = payload.get("message") or payload.get("edited_message")
    if not message:
        return None
    chat = message.get("chat") or {}
    reply_to = (message.get("reply_to_message") or {})
    return {
        "chat_id": str(chat.get("id", "")),
        "text": message.get("text", ""),
        "from_name": (message.get("from") or {}).get("username") or "telegram",
        "reply_to_message_id": reply_to.get("message_id"),  # int or None
    }


# ─── domain-level helpers ────────────────────────────────────────────────────

def notify_admin_new_lead(lead) -> None:
    """Уведомление в TG: новая быстрая заявка (QuickLead)."""
    chat_id = _admin_chat_id()
    if not chat_id:
        return
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    text = (
        "🔔 <b>Новая заявка с сайта</b>\n"
        f"Тип: {lead.get_request_type_display()}\n"
        f"Имя: {lead.name or '—'}\n"
        f"Телефон: {lead.phone or '—'}\n"
        f"Email: {lead.email or '—'}\n"
        f"Размеры: {lead.dimensions or '—'}\n"
        f"Комментарий: {lead.details or '—'}\n\n"
        f"<a href=\"{site_url}/admin/support/quicklead/{lead.pk}/change/\">Открыть в админке</a>"
    )
    send_telegram_message(chat_id, text)


def notify_admin_new_request(thread, first_message_body: str) -> None:
    """Уведомление в TG: новая заявка поддержки (RequestThread)."""
    chat_id = _admin_chat_id()
    if not chat_id:
        return
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    text = (
        "📋 <b>Новая заявка в поддержку</b> "
        f"<code>#{thread.id}</code>\n"
        f"👤 {thread.user.email}\n"
        f"Тема: {thread.subject}\n\n"
        f"{first_message_body[:600]}\n\n"
        f"<a href=\"{site_url}/admin/support/requestthread/{thread.pk}/change/\">Открыть в админке</a>"
    )
    send_telegram_message(chat_id, text)


def notify_admin_chat_message(thread, user_email: str, message_body: str) -> "int | None":
    """Форвардит сообщение из чата администратору в TG.
    Возвращает telegram message_id отправленного сообщения.
    Этот ID сохраняется на конкретном SupportChatMessage, поэтому
    reply на любое сообщение любого из 10 пользователей → правильный тред.
    """
    chat_id = _admin_chat_id()
    if not chat_id:
        return None
    text = (
        f"💬 <b>{user_email}</b>  [чат #{thread.id}]\n"
        "─────────────────────\n"
        f"{message_body[:800]}\n\n"
        "<i>↩ Ответьте на это сообщение → ответ уйдёт этому пользователю на сайт</i>"
    )
    result = send_telegram_message(chat_id, text)
    return _tg_message_id(result)
