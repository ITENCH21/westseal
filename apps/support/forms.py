from django import forms
from .models import RequestThread, RequestMessage, SupportChatMessage, QuickLead


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class RequestCreateForm(forms.ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 6}))
    files = forms.FileField(
        required=False,
        widget=MultiFileInput(attrs={"multiple": True}),
    )

    class Meta:
        model = RequestThread
        fields = ["subject"]


class RequestMessageForm(forms.ModelForm):
    files = forms.FileField(
        required=False,
        widget=MultiFileInput(attrs={"multiple": True}),
    )

    class Meta:
        model = RequestMessage
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 4})}


class ChatMessageForm(forms.ModelForm):
    files = forms.FileField(
        required=False,
        widget=MultiFileInput(
            attrs={
                "multiple": True,
                "class": "chat-file-input",
                "id": "chat-files",
                "accept": "image/*,video/*,application/pdf,.dwg,.dxf",
            }
        ),
    )

    class Meta:
        model = SupportChatMessage
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Опишите задачу или укажите размер уплотнения",
                    "class": "chat-input",
                }
            )
        }


class QuickLeadForm(forms.ModelForm):
    honey = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = QuickLead
        fields = ["name", "email", "phone", "request_type", "dimensions", "details", "file"]
        widgets = {
            "details": forms.Textarea(attrs={"rows": 4, "placeholder": "Опишите задачу, давление, среду, температуру"}),
            "name": forms.TextInput(attrs={"placeholder": "Имя"}),
            "phone": forms.TextInput(attrs={"placeholder": "+7..."}),
            "email": forms.EmailInput(attrs={"placeholder": "email@example.com"}),
            "dimensions": forms.TextInput(attrs={"placeholder": "Например: 50x70x10"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("honey"):
            raise forms.ValidationError("Spam detected")
        if not cleaned.get("phone") and not cleaned.get("email"):
            raise forms.ValidationError("Укажите телефон или email")
        return cleaned
