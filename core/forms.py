from django import forms
from django.urls import reverse

from .models import Societe


class LogoInput(forms.ClearableFileInput):
    """Shows the current logo through the logo view: uploaded files have no public URL."""

    template_name = "core/widgets/logo_input.html"

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["widget"]["preview_url"] = reverse("core:logo")
        return ctx


class SocieteForm(forms.ModelForm):
    class Meta:
        model = Societe
        exclude = ["updated_at"]
        widgets = {"logo": LogoInput}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-control", "rows": 3})
            elif isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs.update({"class": "form-control"})
            else:
                field.widget.attrs.update({"class": "form-control"})
