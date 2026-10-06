from django import forms

from .models import Partner


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = [
            "type_tiers", "raison_sociale", "ice", "rc", "contact_principal",
            "telephone", "email", "adresse", "ville", "pays", "exonere_tva", "motif_exoneration", "notes", "is_active",
        ]
        widgets = {
            "type_tiers": forms.Select(attrs={"class": "form-select"}),
            "raison_sociale": forms.TextInput(attrs={"class": "form-control"}),
            "ice": forms.TextInput(attrs={"class": "form-control"}),
            "rc": forms.TextInput(attrs={"class": "form-control"}),
            "contact_principal": forms.TextInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "adresse": forms.TextInput(attrs={"class": "form-control"}),
            "ville": forms.TextInput(attrs={"class": "form-control"}),
            "pays": forms.TextInput(attrs={"class": "form-control"}),
            "exonere_tva": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "motif_exoneration": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("exonere_tva") and not cleaned.get("motif_exoneration", "").strip():
            self.add_error(
                "motif_exoneration",
                "Indiquez le motif de l'exonération : il doit figurer sur les factures.",
            )
        return cleaned
