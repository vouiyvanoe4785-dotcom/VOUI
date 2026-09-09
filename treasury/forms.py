from django import forms

from .models import CashAccount, CashTransaction


class CashAccountForm(forms.ModelForm):
    class Meta:
        model = CashAccount
        fields = [
            "nom", "type_compte", "devise", "solde_initial", "numero_compte",
            "responsable", "is_active",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "type_compte": forms.Select(attrs={"class": "form-select"}),
            "devise": forms.TextInput(attrs={"class": "form-control"}),
            "solde_initial": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "numero_compte": forms.TextInput(attrs={"class": "form-control"}),
            "responsable": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CashTransactionForm(forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = [
            "type_mouvement", "categorie", "montant", "date_mouvement", "description",
            "dossier", "tiers",
        ]
        widgets = {
            "type_mouvement": forms.Select(attrs={"class": "form-select"}),
            "categorie": forms.Select(attrs={"class": "form-select"}),
            "montant": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "date_mouvement": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "dossier": forms.Select(attrs={"class": "form-select"}),
            "tiers": forms.Select(attrs={"class": "form-select"}),
        }


class TransferForm(forms.Form):
    compte_source = forms.ModelChoiceField(
        queryset=CashAccount.objects.filter(is_active=True),
        label="Compte source", widget=forms.Select(attrs={"class": "form-select"}),
    )
    compte_destination = forms.ModelChoiceField(
        queryset=CashAccount.objects.filter(is_active=True),
        label="Compte destination", widget=forms.Select(attrs={"class": "form-select"}),
    )
    montant = forms.DecimalField(
        max_digits=14, decimal_places=2, label="Montant",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    date_mouvement = forms.DateField(
        label="Date", widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    description = forms.CharField(
        required=False, label="Libellé", widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        cleaned = super().clean()
        source = cleaned.get("compte_source")
        destination = cleaned.get("compte_destination")
        if source and destination and source == destination:
            raise forms.ValidationError(
                "Le compte source et le compte destination doivent être différents."
            )
        return cleaned
