from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from .forms import RegistrationForm, LoginForm


def register_view(request):
    embed_mode = request.GET.get("embed") == "1" or request.POST.get("embed") == "1"
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("account_dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("account_dashboard")
    tpl = "account/register_embed.html" if embed_mode else "account/register.html"
    return render(request, tpl, {"form": form, "page": None, "next_url": next_url, "embed_mode": embed_mode})


def login_view(request):
    embed_mode = request.GET.get("embed") == "1" or request.POST.get("embed") == "1"
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("account_dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.cleaned_data["user"])
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("account_dashboard")
    tpl = "account/login_embed.html" if embed_mode else "account/login.html"
    return render(request, tpl, {"form": form, "page": None, "next_url": next_url, "embed_mode": embed_mode})


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def dashboard_view(request):
    return render(request, "account/dashboard.html", {"page": None})
