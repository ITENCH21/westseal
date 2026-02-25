from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    RequestThread, RequestMessage, RequestAttachment,
    SupportChatThread, SupportChatMessage, SupportChatAttachment,
    QuickLead
)
from .services import send_telegram_message

# ── Заголовки панели администрирования ─────────────────────────
admin.site.site_header = "WESTSEAL — Панель управления"
admin.site.site_title  = "WESTSEAL Admin"
admin.site.index_title = "Административная панель"

# Цвета статусов заявок
_REQUEST_STATUS_COLORS = {
    "sent":           ("#fff3cd", "#856404"),   # жёлтый    — Новая
    "review":         ("#cce5ff", "#004085"),   # синий     — Прочитана
    "in_work":        ("#e0d7ff", "#3d108a"),   # фиолетовый— В работе
    "payment":        ("#ffe0b2", "#7a3800"),   # оранжевый — На оплате
    "paid":           ("#d4edda", "#155724"),   # зелёный   — Оплачено
    "in_transit":     ("#e0f4ff", "#0d47a1"),   # голубой   — В пути
    "answered":       ("#d0f0e0", "#1b5e20"),   # тёмно-зелёный — Поступил ответ
    "closed_success": ("#c8e6c9", "#1b5e20"),   # зелёный   — Закрыта успешно
    "closed_fail":    ("#ffcdd2", "#b71c1c"),   # красный   — Закрыто неуспешно
    "closed":         ("#e2e3e5", "#383d41"),   # серый     — Закрыто
}

# Цвета статусов чата
_CHAT_STATUS_COLORS = {
    "open":   ("#d4edda", "#155724"),
    "closed": ("#e2e3e5", "#383d41"),
}


# ─────────────────────────────────────────────────────────────────
# Заявки (RequestThread)
# ─────────────────────────────────────────────────────────────────

class RequestMessageInline(admin.StackedInline):
    model = RequestMessage
    verbose_name = "Сообщение"
    verbose_name_plural = "Сообщения в заявке"
    extra = 1
    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if not obj.author_id:
                obj.author = request.user
            obj.save()
            form.instance.status = "answered"
            form.instance.save(update_fields=["status", "updated_at"])
        formset.save_m2m()


@admin.register(RequestThread)
class RequestThreadAdmin(admin.ModelAdmin):
    list_display = ("subject", "user_email", "status_badge", "msg_count", "open_request_link", "created_at")
    list_filter  = ("status",)
    search_fields = ("subject", "user__email")
    ordering     = ("-created_at",)
    inlines      = [RequestMessageInline]
    list_per_page = 30

    @admin.display(description="Пользователь", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Статус", ordering="status")
    def status_badge(self, obj):
        bg, fg = _REQUEST_STATUS_COLORS.get(obj.status, ("#eee", "#333"))
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:20px;'
            'font-size:.78rem;font-weight:600;white-space:nowrap;">{}</span>',
            bg, fg, label,
        )

    @admin.display(description="Сообщений")
    def msg_count(self, obj):
        return obj.messages.count()

    @admin.display(description="Открыть")
    def open_request_link(self, obj):
        url = reverse("support_admin_request_thread", args=[obj.pk])
        return format_html(
            '<a href="{}" style="background:linear-gradient(135deg,#d1373d,#1f4a8a);'
            'color:#fff;padding:3px 12px;border-radius:8px;font-size:.8rem;'
            'text-decoration:none;white-space:nowrap;">📋 Заявка</a>',
            url,
        )


@admin.register(RequestAttachment)
class RequestAttachmentAdmin(admin.ModelAdmin):
    list_display = ("message", "file", "uploaded_at")
    search_fields = ("file", "message__thread__subject", "message__author__email")


# ─────────────────────────────────────────────────────────────────
# Чат (SupportChatThread)
# ─────────────────────────────────────────────────────────────────

class SupportChatMessageInline(admin.TabularInline):
    model = SupportChatMessage
    verbose_name = "Сообщение"
    verbose_name_plural = "Сообщения в чате"
    extra = 0
    fields = ("created_at", "author", "via", "is_bot", "is_hidden_by_user", "body_short")
    readonly_fields = ("created_at", "author", "via", "is_bot", "is_hidden_by_user", "body_short")
    ordering = ("-created_at",)
    max_num = 0
    can_delete = False

    @admin.display(description="Текст")
    def body_short(self, obj):
        return obj.body[:120] + ("…" if len(obj.body) > 120 else "")


@admin.register(SupportChatThread)
class SupportChatThreadAdmin(admin.ModelAdmin):
    list_display = (
        "user_email", "chat_status_badge", "unread_badge",
        "messages_count", "updated_at", "open_chat_link",
    )
    list_filter  = ("status",)
    search_fields = ("user__email", "telegram_chat_id", "admin_telegram_chat_id")
    ordering     = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at", "open_chat_link_big")
    fields = (
        "user", "status",
        "telegram_chat_id", "admin_telegram_chat_id",
        "bot_state",
        "created_at", "updated_at",
        "open_chat_link_big",
    )
    inlines = [SupportChatMessageInline]
    list_per_page = 30

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("messages")

    @admin.display(description="Пользователь", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Статус чата", ordering="status")
    def chat_status_badge(self, obj):
        bg, fg = _CHAT_STATUS_COLORS.get(obj.status, ("#eee", "#333"))
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:20px;'
            'font-size:.78rem;font-weight:600;">{}</span>',
            bg, fg, label,
        )

    @admin.display(description="Новых")
    def unread_badge(self, obj):
        count = obj.messages.filter(
            via__in=("site", "telegram"), is_admin_seen=False,
        ).count()
        if count:
            return format_html(
                '<span style="background:#d1373d;color:#fff;padding:2px 9px;'
                'border-radius:20px;font-size:.78rem;font-weight:700;">{}</span>',
                count,
            )
        return "—"

    @admin.display(description="Сообщений")
    def messages_count(self, obj):
        total  = obj.messages.count()
        hidden = obj.messages.filter(is_hidden_by_user=True).count()
        if hidden:
            return f"{total} ({hidden} скр.)"
        return total

    @admin.display(description="Чат")
    def open_chat_link(self, obj):
        url = reverse("support_admin_chat_thread", args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank" style="'
            'background:linear-gradient(135deg,#d1373d,#1f4a8a);'
            'color:#fff;padding:3px 12px;border-radius:8px;font-size:.8rem;'
            'text-decoration:none;white-space:nowrap;">💬 Чат</a>',
            url,
        )

    @admin.display(description="Открыть чат")
    def open_chat_link_big(self, obj):
        if not obj.pk:
            return "—"
        url = reverse("support_admin_chat_thread", args=[obj.pk])
        list_url = reverse("support_admin_chat_list")
        return format_html(
            '<a href="{}" target="_blank" style="font-size:.95rem;font-weight:600;color:#1f4a8a;">'
            '💬 Открыть удобный чат с {}</a>'
            '&nbsp;&nbsp;<a href="{}" style="font-size:.85rem;color:#888;">← все чаты</a>',
            url, obj.user.email, list_url,
        )


@admin.register(SupportChatMessage)
class SupportChatMessageAdmin(admin.ModelAdmin):
    list_display = ("thread_user", "author", "via", "is_bot", "is_hidden_by_user", "body_short", "created_at")
    list_filter = ("via", "is_bot", "is_hidden_by_user")
    search_fields = ("body", "thread__user__email", "author__email")
    readonly_fields = ("thread", "author", "created_at")
    actions = ["send_to_telegram"]

    @admin.display(description="Пользователь чата", ordering="thread__user__email")
    def thread_user(self, obj):
        return obj.thread.user.email

    @admin.display(description="Сообщение")
    def body_short(self, obj):
        return obj.body[:80] + ("…" if len(obj.body) > 80 else "")

    @admin.action(description="Отправить в Telegram (telegram_chat_id треда)")
    def send_to_telegram(self, request, queryset):
        sent = 0
        for msg in queryset:
            chat_id = msg.thread.telegram_chat_id
            if chat_id:
                send_telegram_message(chat_id, msg.body)
                sent += 1
        self.message_user(request, f"Отправлено {sent} сообщений в Telegram.")


@admin.register(SupportChatAttachment)
class SupportChatAttachmentAdmin(admin.ModelAdmin):
    list_display = ("message", "file", "uploaded_at")
    search_fields = ("file", "message__thread__user__email")


# ─────────────────────────────────────────────────────────────────
# Быстрые заявки
# ─────────────────────────────────────────────────────────────────

@admin.register(QuickLead)
class QuickLeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "request_type", "source_page", "created_at")
    list_filter = ("request_type",)
    search_fields = ("name", "phone", "email", "details", "dimensions")
    readonly_fields = ("created_at",)
