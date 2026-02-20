from django.db import models
from django.conf import settings
from django.utils import timezone


class RequestStatus(models.TextChoices):
    SENT = "sent", "Отправлено"
    IN_REVIEW = "review", "На проверке"
    ANSWERED = "answered", "Поступил ответ"
    CLOSED = "closed", "Закрыто"


class RequestThread(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.SENT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.subject} ({self.get_status_display()})"


class RequestMessage(models.Model):
    thread = models.ForeignKey(RequestThread, related_name="messages", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.author.email}: {self.body[:30]}"


class RequestAttachment(models.Model):
    message = models.ForeignKey(RequestMessage, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to="requests/attachments/")
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.file.name


class ChatStatus(models.TextChoices):
    OPEN = "open", "Открыт"
    CLOSED = "closed", "Закрыт"


class SupportChatThread(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=ChatStatus.choices, default=ChatStatus.OPEN)
    telegram_chat_id = models.CharField(max_length=60, blank=True)
    # Bot conversation state: {"stage": "...", "query": "...", "found_ids": [...]}
    bot_state = models.JSONField(default=dict, blank=True)
    # Telegram chat id for ADMIN-side bot (replies to user)
    admin_telegram_chat_id = models.CharField(max_length=60, blank=True,
        help_text="Chat ID в ТГ-группе/личке для уведомлений администраторов")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Chat {self.user.email}"


class SupportChatMessage(models.Model):
    thread = models.ForeignKey(SupportChatThread, related_name="messages", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    via = models.CharField(max_length=20, default="site")  # site / telegram / admin / bot
    is_bot = models.BooleanField(default=False)
    is_hidden_by_user = models.BooleanField(default=False,
        help_text="Скрыто клиентом (очистка беседы). В БД сохраняется.")
    # TG message_id форварда этого сообщения администратору.
    # Reply на этот ID в чате Ивана → ответ уйдёт именно этому пользователю на сайт.
    admin_tg_message_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        help_text="Telegram message_id форварда администратору (для reply-роутинга)",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.author.email}: {self.body[:30]}"


class SupportChatAttachment(models.Model):
    message = models.ForeignKey(SupportChatMessage, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to="chat/attachments/")
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.file.name


class QuickLead(models.Model):
    REQUEST_TYPE_CHOICES = [
        ("analogue", "Подбор аналога"),
        ("manufacture", "Изготовление"),
        ("supply", "Поставка"),
    ]
    name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    request_type = models.CharField(max_length=30, choices=REQUEST_TYPE_CHOICES, default="analogue")
    dimensions = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)
    file = models.FileField(upload_to="leads/files/", blank=True, null=True)
    source_page = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.phone or self.email or f"Lead {self.pk}"
