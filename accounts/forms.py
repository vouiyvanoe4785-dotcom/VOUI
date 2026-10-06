from django import forms
from django.contrib.auth.forms import UserCreationForm

from partners.models import Partner, PartnerType

from .models import Role, User


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "role", "partner", "phone", "service", "recap_alertes_email")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "partner": forms.Select(attrs={"class": "form-select"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "service": forms.TextInput(attrs={"class": "form-control"}),
            "recap_alertes_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control"})
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})
        self.fields["partner"].queryset = Partner.objects.filter(
            type_tiers=PartnerType.CLIENT, is_active=True
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == Role.CLIENT:
            if not cleaned.get("partner"):
                self.add_error("partner", "Choisissez la société cliente à laquelle ce compte donne accès.")
            if not cleaned.get("email"):
                self.add_error("email", "Obligatoire pour un client : c'est là qu'il recevra le lien « mot de passe oublié ».")
        else:
            cleaned["partner"] = None
        return cleaned
