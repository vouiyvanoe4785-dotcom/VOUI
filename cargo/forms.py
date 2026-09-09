from django import forms

from .models import Marchandise


class MarchandiseForm(forms.ModelForm):
    class Meta:
        model = Marchandise
        fields = [
            "designation", "code_hs", "quantite", "unite", "colisage",
            "poids_brut", "poids_net", "valeur", "devise", "origine", "notes",
        ]
        widgets = {
            "designation": forms.TextInput(attrs={"class": "form-control"}),
            "code_hs": forms.TextInput(attrs={"class": "form-control"}),
            "quantite": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unite": forms.TextInput(attrs={"class": "form-control"}),
            "colisage": forms.TextInput(attrs={"class": "form-control"}),
            "poids_brut": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "poids_net": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "valeur": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "devise": forms.TextInput(attrs={"class": "form-control"}),
            "origine": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
