from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="account_login"),
    path("register/", views.register_view, name="account_register"),
    path("logout/", views.logout_view, name="account_logout"),
    path("", views.dashboard_view, name="account_dashboard"),
]
