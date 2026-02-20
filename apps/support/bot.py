"""
EURO-SEAL Chat Bot
==================
Автоматический помощник с конечным автоматом состояний.

Этапы диалога (bot_state["stage"]):
  greet        — первое приветствие, предлагаем помочь
  ask_product  — спрашиваем что нужно
  searching    — ищем по базе
  show_results — показали результаты, ждём уточнений / готовности к заявке
  ask_contact  — уточняем контакт для звонка
  done         — заявка создана, диалог завершён, ждём менеджера

Будущее расширение:
  - Когда у SealProduct появится поле `price`, возвращать цену в show_results
  - Этап invoice_create — автоматически формировать счёт
"""

from __future__ import annotations

import re
from typing import Optional

from django.conf import settings
from django.utils import timezone

# ────────────────────────────────────────────────────────────────
# Тексты фраз
# ────────────────────────────────────────────────────────────────

MSG_GREET = (
    "Здравствуйте! 👋 Я автоматический помощник EURO-SEAL.\n"
    "Помогу подобрать уплотнения под вашу задачу.\n\n"
    "Напишите название, размер или тип изделия — например: "
    "«О-кольцо 50×3» или «манжета штока 40мм»."
)

MSG_SEARCHING = "🔍 Ищу подходящие позиции по запросу «{query}»…"

MSG_RESULTS_FOUND = (
    "Нашёл {count} подходящих позиций по запросу «{query}»:\n\n"
    "{items}\n\n"
    "Если нашли нужное — напишите его номер или название для уточнения.\n"
    "Если нужна цена или хотите оформить заявку — напишите «заявка» или своё имя и телефон."
)

MSG_NO_RESULTS = (
    "К сожалению, по запросу «{query}» ничего не нашёл в базе.\n\n"
    "Попробуйте уточнить — например, укажите материал (резина, полиуретан, PTFE), "
    "диаметр или ГОСТ. Или напишите «менеджер» — подключим специалиста."
)

MSG_ASK_CONTACT = (
    "Отлично! Чтобы менеджер подготовил предложение и уточнил наличие и цены, "
    "пожалуйста, укажите ваше имя и номер телефона 📞"
)

MSG_DONE = (
    "✅ Спасибо, {name}! Заявка принята.\n"
    "Менеджер свяжется с вами в ближайшее время.\n\n"
    "Если есть ещё вопросы — пишите, я здесь."
)

MSG_MANAGER = (
    "Хорошо, сейчас подключу менеджера. Он ответит в рабочее время (пн–пт, 9:00–18:00 МСК).\n"
    "Если хотите ускорить — оставьте телефон 📞"
)

MSG_HELP = (
    "Чем могу помочь? 😊\n\n"
    "EURO-SEAL подбирает уплотнения для гидравлики и пневматики:\n"
    "• манжеты, сальники, поршневые кольца\n"
    "• уплотнения штока, поршня, фланца\n"
    "• материалы: резина, полиуретан, PTFE, NBR, FKM и др.\n\n"
    "Напишите название или размер изделия, и я подберу варианты из нашей базы —"
    " или оставьте заявку и менеджер свяжется с вами лично."
)

MSG_FALLBACK = (
    "Не совсем понял ваш запрос. Попробуйте описать, какое уплотнение вам нужно "
    "(тип, размер, материал) — или напишите «менеджер» для связи со специалистом."
)

# ────────────────────────────────────────────────────────────────
# Триггерные фразы
# ────────────────────────────────────────────────────────────────

# Только когда сообщение состоит ТОЛЬКО из приветствия (с возможной пунктуацией)
GREET_TRIGGERS = re.compile(
    r"^\s*(привет|здравствуй\w*|добрый\s+\w+|хай|hello|hi)[!.,\s]*$",
    re.IGNORECASE | re.UNICODE,
)

MANAGER_TRIGGERS = re.compile(
    r"\b(менеджер|оператор|человек|специалист|позвон|connect|manager)\b",
    re.IGNORECASE | re.UNICODE,
)

LEAD_TRIGGERS = re.compile(
    r"\b(заявк|счёт|счет|invoice|купить|заказ|стоимость|цен|прайс|price)\b",
    re.IGNORECASE | re.UNICODE,
)

# Фразы «нужна помощь», «помогите» и подобные — без конкретного запроса
HELP_TRIGGERS = re.compile(
    r"^\s*(мне\s+)?(нужна?\s+помощь|помогите|поможите|помоги\b|есть\s+вопросы?|help)[!?.,\s]*$",
    re.IGNORECASE | re.UNICODE,
)

# Имя + телефон в одном сообщении — типа «Иван 89991234567»
CONTACT_RE = re.compile(
    r"(?P<name>[А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+)?)"
    r"[\s,]+(?P<phone>[+7\d][\d\s\-()]{7,14})",
    re.UNICODE,
)


# ────────────────────────────────────────────────────────────────
# Вспомогательные
# ────────────────────────────────────────────────────────────────

def _get_bot_user():
    """Возвращает суперпользователя как «автора» ботовых сообщений."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    bot = User.objects.filter(is_superuser=True).order_by("id").first()
    if bot is None:
        bot = User.objects.filter(is_staff=True).order_by("id").first()
    return bot


def _search_products(query: str, limit: int = 5):
    """Возвращает список SealProduct, найденных по запросу."""
    try:
        from apps.core.models import SealProduct
        from apps.core.search import seal_product_search
        qs = SealProduct.objects.all()
        results = seal_product_search(qs, query, limit=limit)
        return list(results[:limit])
    except Exception:
        return []


def _format_product_list(products) -> str:
    lines = []
    for i, p in enumerate(products, 1):
        name = p.name[:80]
        url = f"http://{getattr(settings, 'ALLOWED_HOSTS', ['127.0.0.1'])[0]}/catalog/product/{p.pk}/"
        lines.append(f"{i}. {name}")
    return "\n".join(lines)


def _save_bot_message(thread, text: str) -> None:
    """Сохраняет сообщение бота в БД и бродкастит через WebSocket."""
    from apps.support.models import SupportChatMessage
    from apps.support.views import _broadcast_chat_message

    bot_user = _get_bot_user()
    if bot_user is None:
        return

    msg = SupportChatMessage.objects.create(
        thread=thread,
        author=bot_user,
        body=text,
        via="bot",
        is_bot=True,
    )
    try:
        _broadcast_chat_message(msg)
    except Exception:
        pass


def _create_quick_lead(thread, name: str, phone: str) -> None:
    from apps.support.models import QuickLead
    state = thread.bot_state or {}
    query = state.get("query", "")
    QuickLead.objects.create(
        name=name,
        phone=phone,
        request_type="callback",
        details=f"Запрос из чата #{thread.id}. Поиск: {query}",
        source_page=f"/support/chat/",
    )


# ────────────────────────────────────────────────────────────────
# Главная точка входа
# ────────────────────────────────────────────────────────────────

def handle_user_message(thread, user_text: str) -> Optional[str]:
    """
    Принимает тред и текст нового сообщения пользователя.
    Обновляет thread.bot_state, сохраняет ответ бота и возвращает текст ответа.
    Возвращает None если бот молчит (например, менеджер уже подключён).
    """
    state: dict = dict(thread.bot_state or {})
    stage: str = state.get("stage", "greet")
    text = user_text.strip()

    # ── Если менеджер уже подключился (stage == done) — бот молчит ──
    if stage == "done":
        return None

    # ── Триггер «менеджер» из любого состояния ──
    if MANAGER_TRIGGERS.search(text):
        state["stage"] = "done"
        _flush_state(thread, state)
        reply = MSG_MANAGER
        _save_bot_message(thread, reply)
        return reply

    # ── Приветствие — из любой стадии ──
    if GREET_TRIGGERS.search(text):
        state["stage"] = "ask_product"
        _flush_state(thread, state)
        reply = MSG_GREET
        _save_bot_message(thread, reply)
        return reply

    # ── «Нужна помощь» / «помогите» — рассказываем о себе и приглашаем уточнить ──
    if HELP_TRIGGERS.search(text):
        state["stage"] = "ask_product"
        _flush_state(thread, state)
        reply = MSG_HELP
        _save_bot_message(thread, reply)
        return reply

    # ── Первое сообщение (не приветствие) — сразу считаем запросом товара ──
    if stage == "greet":
        stage = "ask_product"
        state["stage"] = "ask_product"

    # ── Ожидаем запрос / уточнение ──
    if stage in ("ask_product", "show_results"):
        # Проверяем триггер заявки
        if LEAD_TRIGGERS.search(text):
            state["stage"] = "ask_contact"
            _flush_state(thread, state)
            reply = MSG_ASK_CONTACT
            _save_bot_message(thread, reply)
            return reply

        # Ищем товары
        products = _search_products(text, limit=5)
        state["query"] = text
        state["found_ids"] = [p.pk for p in products]

        if products:
            items = _format_product_list(products)
            reply = MSG_RESULTS_FOUND.format(
                count=len(products), query=text, items=items
            )
            state["stage"] = "show_results"
        else:
            reply = MSG_NO_RESULTS.format(query=text)
            state["stage"] = "ask_product"

        _flush_state(thread, state)
        _save_bot_message(thread, reply)
        return reply

    # ── Ожидаем контакт ──
    if stage == "ask_contact":
        m = CONTACT_RE.search(text)
        if m:
            name = m.group("name").strip()
            phone = re.sub(r"[^\d+]", "", m.group("phone"))
            _create_quick_lead(thread, name, phone)
            state["stage"] = "done"
            state["contact_name"] = name
            _flush_state(thread, state)
            reply = MSG_DONE.format(name=name)
            _save_bot_message(thread, reply)
            return reply
        # Телефон без имени
        phone_only = re.search(r"[+7\d][\d\s\-()]{7,14}", text)
        if phone_only:
            phone = re.sub(r"[^\d+]", "", phone_only.group())
            _create_quick_lead(thread, "—", phone)
            state["stage"] = "done"
            _flush_state(thread, state)
            reply = MSG_DONE.format(name="")
            _save_bot_message(thread, reply)
            return reply
        # Не распознали контакт — напоминаем
        reply = "Пожалуйста, укажите имя и телефон — например: «Иван +7 999 123-45-67»"
        _save_bot_message(thread, reply)
        return reply

    # ── Fallback ──
    _save_bot_message(thread, MSG_FALLBACK)
    return MSG_FALLBACK


def _flush_state(thread, state: dict) -> None:
    thread.bot_state = state
    thread.save(update_fields=["bot_state"])
