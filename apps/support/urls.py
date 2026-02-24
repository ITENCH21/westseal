from django.urls import path
from . import views

urlpatterns = [
    path("requests/", views.request_list, name="support_requests"),
    path("requests/new/", views.request_create, name="support_request_create"),
    path("requests/<int:thread_id>/", views.request_detail, name="support_request_detail"),
    path("quick-lead/", views.quick_lead_create, name="support_quick_lead"),
    path("chat/", views.chat_view, name="support_chat"),
    path("chat/messages/", views.chat_messages_api, name="support_chat_messages"),
    path("chat/clear/", views.chat_clear, name="support_chat_clear"),
    path("telegram/webhook/", views.telegram_webhook, name="support_telegram_webhook"),
    # Admin chat (staff-only)
    path("admin-chat/", views.admin_chat_list, name="support_admin_chat_list"),
    path("admin-chat/<int:thread_id>/", views.admin_chat_thread, name="support_admin_chat_thread"),
    path("admin-chat/<int:thread_id>/reply/", views.admin_chat_reply, name="support_admin_chat_reply"),
    path("admin-chat/<int:thread_id>/messages/", views.admin_chat_messages_api, name="support_admin_chat_messages_api"),
    # Admin requests (staff-only)
    path("admin-requests/", views.admin_requests_list, name="support_admin_requests_list"),
    path("admin-requests/<int:thread_id>/", views.admin_request_thread, name="support_admin_request_thread"),
    path("admin-requests/<int:thread_id>/reply/", views.admin_request_reply, name="support_admin_request_reply"),
    path("admin-requests/<int:thread_id>/status/", views.admin_request_set_status, name="support_admin_request_set_status"),
    # Counts API (for sidebar badges)
    path("admin-counts/", views.admin_counts_api, name="support_admin_counts"),
]
