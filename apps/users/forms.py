import time
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User

# Минимальное время заполнения формы (секунды). Боты отправляют мгновенно.
_MIN_FILL_SECONDS = 3


class RegistrationForm(forms.ModelForm):
    # Honeypot: скрыт CSS/tabindex. Реальный пользователь не заполняет.
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "tabindex": "-1",
            "autocomplete": "off",
            "aria-hidden": "true",
        }),
    )
    # Метка времени загрузки формы, проставляется JS.
    reg_ts = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"id": "id_password1", "autocomplete": "new-password"}),
        label="Пароль",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"id": "id_password2", "autocomplete": "new-password"}),
        label="Повторите пароль",
    )

    class Meta:
        model = User
        fields = ["email", "phone", "first_name", "last_name"]

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned = super().clean()

        # ── Honeypot check ─────────────────────────────────────────────
        if cleaned.get("website"):
            # Бот заполнил ловушку — тихо блокируем (не показываем ошибку).
            raise forms.ValidationError("")

        # ── Timing check ───────────────────────────────────────────────
        ts_raw = cleaned.get("reg_ts", "")
        if ts_raw:
            try:
                ts = float(ts_raw)
                if (time.time() - ts) < _MIN_FILL_SECONDS:
                    raise forms.ValidationError("")
            except (ValueError, TypeError):
                pass  # Если JS не установил — не блокируем

        # ── Password match ─────────────────────────────────────────────
        if cleaned.get("password1") and cleaned.get("password2"):
            if cleaned["password1"] != cleaned["password2"]:
                self.add_error("password2", "Пароли не совпадают")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        user = authenticate(email=cleaned.get("email"), password=cleaned.get("password"))
        if not user:
            raise forms.ValidationError("Invalid credentials")
        cleaned["user"] = user
        return cleaned
