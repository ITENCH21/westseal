from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    RequestThread, RequestMessage, RequestAttachment,
    SupportChatThread, SupportChatMessage, SupportChatAttachment,
    QuickLead
)
from .services import send_telegram_message


# ─────────────────────────────────────────────────────────────────
# Заявки (RequestThread)
# ─────────────────────────────────────────────────────────────────

class RequestMessageInline(admin.StackedInline):
    model = RequestMessage
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
    list_display = ("subject", "user", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("subject", "user__email")
    inlines = [RequestMessageInline]


@admin.register(RequestAttachment)
class RequestAttachmentAdmin(admin.ModelAdmin):
    list_display = ("message", "file", "uploaded_at")
    search_fields = ("file", "message__thread__subject", "message__author__email")


# ─────────────────────────────────────────────────────────────────
# Чат (SupportChatThread)
# ─────────────────────────────────────────────────────────────────

class SupportChatMessageInline(admin.TabularInline):
    model = SupportChatMessage
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
        "user_email", "status", "messages_count",
        "telegram_chat_id", "admin_telegram_chat_id",
        "updated_at", "open_chat_link",
    )
    list_filter = ("status",)
    search_fields = ("user__email", "telegram_chat_id", "admin_telegram_chat_id")
    readonly_fields = ("created_at", "updated_at", "open_chat_link_big")
    fields = (
        "user", "status",
        "telegram_chat_id", "admin_telegram_chat_id",
        "bot_state",
        "created_at", "updated_at",
        "open_chat_link_big",
    )
    inlines = [SupportChatMessageInline]

    @admin.display(description="Пользователь", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Сообщений")
    def messages_count(self, obj):
        total = obj.messages.count()
        hidden = obj.messages.filter(is_hidden_by_user=True).count()
        if hidden:
            return f"{total} ({hidden} скрыто)"
        return total

    @admin.display(description="Открыть чат")
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
