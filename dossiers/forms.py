from django import forms

from .models import Dossier


class DossierForm(forms.ModelForm):
    class Meta:
        model = Dossier
        fields = [
            "client", "reference_client", "donneur_ordre", "type_operation",
            "regime_douanier", "incoterm", "origine", "provenance", "destination",
            "agent_responsable", "statut", "date_cloture", "notes",
        ]
        widgets = {
            "client": forms.Select(attrs={"class": "form-select"}),
            "reference_client": forms.TextInput(attrs={"class": "form-control"}),
            "donneur_ordre": forms.TextInput(attrs={"class": "form-control"}),
            "type_operation": forms.Select(attrs={"class": "form-select"}),
            "regime_douanier": forms.Select(attrs={"class": "form-select"}),
            "incoterm": forms.Select(attrs={"class": "form-select"}),
            "origine": forms.TextInput(attrs={"class": "form-control"}),
            "provenance": forms.TextInput(attrs={"class": "form-control"}),
            "destination": forms.TextInput(attrs={"class": "form-control"}),
            "agent_responsable": forms.Select(attrs={"class": "form-select"}),
            "statut": forms.Select(attrs={"class": "form-select"}),
            "date_cloture": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
