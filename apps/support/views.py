import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from .models import (
    RequestThread, RequestMessage, RequestAttachment,
    SupportChatThread, SupportChatMessage, SupportChatAttachment,
    QuickLead, RequestStatus
)
from .forms import RequestCreateForm, RequestMessageForm, ChatMessageForm, QuickLeadForm
from .services import (
    send_telegram_message, parse_telegram_update, send_admin_notification,
    notify_admin_new_lead, notify_admin_new_request, notify_admin_chat_message,
)
from .bot import handle_user_message as bot_handle


def _chat_redirect(embed_mode: bool):
    return redirect("/support/chat/?embed=1" if embed_mode else "/support/chat/")


def _attachment_type(file_url: str) -> str:
    low = (file_url or "").lower()
    if low.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return "image"
    if low.endswith((".mp4", ".webm", ".ogg", ".mov")):
        return "video"
    return "file"


def _serialize_chat_message(msg: SupportChatMessage, current_user_id: int | None = None) -> dict:
    attachments = []
    for attachment in msg.attachments.all():
        file_url = attachment.file.url if attachment.file else ""
        attachments.append(
            {
                "url": file_url,
                "name": attachment.file.name.rsplit("/", 1)[-1] if attachment.file else "",
                "type": _attachment_type(file_url),
            }
        )
    return {
        "id": msg.id,
        "mine": bool(current_user_id and msg.author_id == current_user_id),
        "author": msg.author.email,
        "body": msg.body,
        "via": msg.via,
        "is_bot": msg.is_bot,
        "created": timezone.localtime(msg.created_at).strftime("%d.%m.%Y %H:%M"),
        "attachments": attachments,
    }


def _broadcast_chat_message(msg: SupportChatMessage):
    layer = get_channel_layer()
    if not layer:
        return
    payload = _serialize_chat_message(msg)
    payload["mine"] = False
    async_to_sync(layer.group_send)(
        f"support_chat_{msg.thread_id}",
        {
            "type": "chat_message",
            "message": payload,
        },
    )


@login_required
def request_list(request):
    threads = RequestThread.objects.filter(user=request.user)
    return render(request, "support/requests_list.html", {"threads": threads, "page": None})


@login_required
def request_create(request):
    form = RequestCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        thread = form.save(commit=False)
        thread.user = request.user
        thread.status = RequestStatus.SENT
        thread.save()
        msg = RequestMessage.objects.create(
            thread=thread,
            author=request.user,
            body=form.cleaned_data["message"],
        )
        for f in request.FILES.getlist("files"):
            RequestAttachment.objects.create(message=msg, file=f)
        send_admin_notification(
            "Новая заявка EURO-SEAL",
            (
                f"Тема: {thread.subject}\n"
                f"Пользователь: {request.user.email}\n"
                f"Статус: {thread.get_status_display()}\n"
                f"ID заявки: {thread.id}"
            ),
        )
        # TG-уведомление администратору
        try:
            notify_admin_new_request(thread, form.cleaned_data["message"])
        except Exception:
            pass
        return redirect("support_request_detail", thread_id=thread.id)
    return render(request, "support/request_create.html", {"form": form, "page": None})


@login_required
def request_detail(request, thread_id):
    thread = get_object_or_404(RequestThread, pk=thread_id, user=request.user)
    form = RequestMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        msg = form.save(commit=False)
        msg.thread = thread
        msg.author = request.user
        msg.save()
        for f in request.FILES.getlist("files"):
            RequestAttachment.objects.create(message=msg, file=f)
        thread.status = RequestStatus.IN_REVIEW
        thread.save(update_fields=["status", "updated_at"])
        send_admin_notification(
            f"Новый ответ в заявке #{thread.id}",
            (
                f"Пользователь: {request.user.email}\n"
                f"Тема: {thread.subject}\n"
                f"Текст: {msg.body[:600]}"
            ),
        )
        return redirect("support_request_detail", thread_id=thread.id)
    return render(request, "support/request_detail.html", {"thread": thread, "form": form, "page": None})


def chat_view(request):
    embed_mode = request.GET.get("embed") == "1" or request.POST.get("embed") == "1"
    if not request.user.is_authenticated:
        if embed_mode:
            return render(request, "support/chat_guest_embed.html", {"page": None})
        login_url = reverse("account_login")
        return redirect(f"{login_url}?next=/support/chat/")

    thread, _ = SupportChatThread.objects.get_or_create(user=request.user)
    form = ChatMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        last_post_ts = request.session.get("chat_last_post_ts")
        now = timezone.now().timestamp()
        if last_post_ts and (now - float(last_post_ts)) < 2:
            messages.error(request, "Слишком частая отправка. Подождите пару секунд.")
            return _chat_redirect(embed_mode)
        msg = form.save(commit=False)
        msg.thread = thread
        msg.author = request.user
        msg.via = "site"
        msg.save()
        for f in request.FILES.getlist("files"):
            SupportChatAttachment.objects.create(message=msg, file=f)
        _broadcast_chat_message(msg)
        request.session["chat_last_post_ts"] = str(now)
        if thread.telegram_chat_id:
            send_telegram_message(thread.telegram_chat_id, msg.body)
        send_admin_notification(
            f"Новое сообщение в чате #{thread.id}",
            (
                f"Пользователь: {request.user.email}\n"
                f"Канал: {msg.via}\n"
                f"Текст: {msg.body[:600]}"
            ),
        )
        # Форвард администратору в TG; сохраняем message_id для reply-роутинга
        try:
            tg_msg_id = notify_admin_chat_message(thread, request.user.email, msg.body)
            if tg_msg_id:
                # Храним ID на конкретном сообщении — не на треде.
                # Reply на любое сообщение (10 разных пользователей) →
                # ответ уйдёт именно этому пользователю.
                msg.admin_tg_message_id = tg_msg_id
                msg.save(update_fields=["admin_tg_message_id"])
        except Exception:
            pass
        # Бот отвечает автоматически (если не подключён менеджер)
        try:
            bot_handle(thread, msg.body)
        except Exception:
            pass
        return _chat_redirect(embed_mode)
    template_name = "support/chat_embed.html" if embed_mode else "support/chat.html"
    ws_path = f"/ws/support/chat/{thread.id}/"
    return render(request, template_name, {"thread": thread, "form": form, "ws_path": ws_path, "page": None})


@login_required
def chat_messages_api(request):
    thread = get_object_or_404(SupportChatThread, user=request.user)
    try:
        after_id = int(request.GET.get("after_id", "0"))
    except (TypeError, ValueError):
        after_id = 0
    queryset = (
        thread.messages
        .filter(id__gt=after_id, is_hidden_by_user=False)
        .select_related("author")
        .prefetch_related("attachments")
        .order_by("id")[:60]
    )
    payload = []
    for msg in queryset:
        payload.append(_serialize_chat_message(msg, request.user.id))
    return JsonResponse({"messages": payload})


@login_required
@require_POST
def chat_clear(request):
    """Клиент очищает беседу: сообщения скрываются у него, в БД остаются."""
    thread = get_object_or_404(SupportChatThread, user=request.user)
    thread.messages.all().update(is_hidden_by_user=True)
    # Сбрасываем bot_state чтобы следующий диалог начался заново
    thread.bot_state = {}
    thread.save(update_fields=["bot_state", "updated_at"])
    embed_mode = request.POST.get("embed") == "1"
    return _chat_redirect(embed_mode)


def quick_lead_create(request):
    if request.method != "POST":
        return redirect("home")

    # Light anti-spam throttle for public form
    key = f"lead_last_post_{request.META.get('REMOTE_ADDR', 'unknown')}"
    last_post_ts = request.session.get(key)
    now = timezone.now().timestamp()
    if last_post_ts and (now - float(last_post_ts)) < 8:
        messages.error(request, "Слишком частая отправка формы. Повторите через несколько секунд.")
        return redirect(request.POST.get("source_page") or "home")

    form = QuickLeadForm(request.POST, request.FILES)
    if form.is_valid():
        lead = form.save(commit=False)
        lead.source_page = request.POST.get("source_page", "")
        lead.save()
        send_admin_notification(
            "Новая быстрая заявка EURO-SEAL",
            (
                f"Тип: {lead.get_request_type_display()}\n"
                f"Имя: {lead.name or '-'}\n"
                f"Телефон: {lead.phone or '-'}\n"
                f"Email: {lead.email or '-'}\n"
                f"Размеры: {lead.dimensions or '-'}\n"
                f"Источник: {lead.source_page or '-'}\n"
                f"Комментарий: {lead.details or '-'}"
            ),
        )
        # TG-уведомление администратору
        try:
            notify_admin_new_lead(lead)
        except Exception:
            pass
        request.session[key] = str(now)
        messages.success(request, "Заявка отправлена. Инженер свяжется с вами.")
    else:
        messages.error(request, "Проверьте форму: укажите телефон или email.")

    return redirect(request.POST.get("source_page") or "home")


@csrf_exempt
def telegram_webhook(request):
    if settings.TELEGRAM_WEBHOOK_SECRET and request.GET.get("secret") != settings.TELEGRAM_WEBHOOK_SECRET:
        return HttpResponseForbidden("forbidden")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False})

    parsed = parse_telegram_update(payload)
    if not parsed or not parsed["chat_id"] or not parsed.get("text"):
        return JsonResponse({"ok": True})

    admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    reply_to_id = parsed.get("reply_to_message_id")

    # ── 1. Ответ администратора (Ivan отвечает reply на любое сообщение в своей личке) ──
    # Каждое сообщение пользователя имеет свой admin_tg_message_id →
    # reply на любое из них (10 разных пользователей) → правильный тред.
    if admin_chat_id and parsed["chat_id"] == str(admin_chat_id) and reply_to_id:
        site_msg = (
            SupportChatMessage.objects
            .filter(admin_tg_message_id=reply_to_id)
            .select_related("thread", "thread__user")
            .first()
        )
        if site_msg:
            thread = site_msg.thread
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_user = User.objects.filter(is_staff=True).order_by("pk").first() or thread.user
            reply_msg = SupportChatMessage.objects.create(
                thread=thread,
                author=admin_user,
                body=parsed["text"],
                via="telegram",
            )
            _broadcast_chat_message(reply_msg)
            send_telegram_message(
                admin_chat_id,
                f"✅ Доставлено → {thread.user.email}: «{parsed['text'][:120]}»",
            )
            return JsonResponse({"ok": True})

    # ── 2. Сообщение от пользователя через его личный ТГ (telegram_chat_id на треде) ──
    thread = SupportChatThread.objects.filter(telegram_chat_id=parsed["chat_id"]).first()
    if thread:
        msg = SupportChatMessage.objects.create(
            thread=thread,
            author=thread.user,
            body=parsed["text"],
            via="telegram",
        )
        _broadcast_chat_message(msg)

    return JsonResponse({"ok": True})


# ─────────────────────────────────────────────────────────────────
# Admin chat views (staff-only)
# ─────────────────────────────────────────────────────────────────

@staff_member_required
def admin_chat_list(request):
    """Список всех активных чатов для быстрого доступа."""
    threads = (
        SupportChatThread.objects
        .select_related("user")
        .prefetch_related("messages")
        .order_by("-updated_at")
    )
    # Добавим счётчик непрочитанных (сообщений не от бота)
    for t in threads:
        t.unread_count = t.messages.filter(
            via__in=("site", "telegram"),
            is_hidden_by_user=False,
        ).count()
    return render(request, "support/admin_chat_list.html", {"threads": threads})


@staff_member_required
def admin_chat_thread(request, thread_id):
    """Полноэкранный чат с конкретным пользователем."""
    thread = get_object_or_404(SupportChatThread, pk=thread_id)
    msgs = (
        thread.messages
        .select_related("author")
        .prefetch_related("attachments")
        .order_by("created_at")
    )
    ws_path = f"/ws/support/chat/{thread.id}/"
    return render(request, "support/admin_chat_thread.html", {
        "thread": thread,
        "msgs": msgs,
        "ws_path": ws_path,
        "api_url": reverse("support_admin_chat_messages_api", args=[thread_id]),
    })


@staff_member_required
@require_POST
def admin_chat_reply(request, thread_id):
    """Admins send a reply. Broadcasts via WS + optionally Telegram."""
    thread = get_object_or_404(SupportChatThread, pk=thread_id)
    body = (request.POST.get("body") or "").strip()
    if not body:
        return JsonResponse({"ok": False, "error": "empty"})

    msg = SupportChatMessage.objects.create(
        thread=thread,
        author=request.user,
        body=body,
        via="admin",
    )
    # WebSocket broadcast to the user's chat
    _broadcast_chat_message(msg)

    # Telegram: notify user if thread has telegram_chat_id
    if thread.telegram_chat_id:
        send_telegram_message(
            thread.telegram_chat_id,
            f"Менеджер EURO-SEAL: {body}",
        )

    # Telegram: notify admin group if configured
    if thread.admin_telegram_chat_id:
        send_telegram_message(
            thread.admin_telegram_chat_id,
            f"[Ответ отправлен] {request.user.email} → {thread.user.email}:\n{body}",
        )

    return JsonResponse({
        "ok": True,
        "message": _serialize_chat_message(msg, request.user.id),
    })


@staff_member_required
def admin_chat_messages_api(request, thread_id):
    """Polling API for admin chat: returns ALL (not hidden) messages after after_id."""
    thread = get_object_or_404(SupportChatThread, pk=thread_id)
    try:
        after_id = int(request.GET.get("after_id", "0"))
    except (TypeError, ValueError):
        after_id = 0
    queryset = (
        thread.messages
        .filter(id__gt=after_id)
        .select_related("author")
        .prefetch_related("attachments")
        .order_by("id")[:80]
    )
    msgs = [_serialize_chat_message(m, request.user.id) for m in queryset]
    return JsonResponse({"messages": msgs})
