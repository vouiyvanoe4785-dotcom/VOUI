from django import forms
from django.forms import inlineformset_factory

from .models import Quote, QuoteLine, Invoice, InvoiceLine, Payment, Reminder

LINE_WIDGETS = {
    "type_frais": forms.Select(attrs={"class": "form-select form-select-sm"}),
    "designation": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    "quantite": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01"}),
    "prix_unitaire": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01"}),
}


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ["type_devis", "dossier", "client", "statut", "date_validite", "notes"]
        widgets = {
            "type_devis": forms.Select(attrs={"class": "form-select"}),
            "dossier": forms.Select(attrs={"class": "form-select"}),
            "client": forms.Select(attrs={"class": "form-select"}),
            "statut": forms.Select(attrs={"class": "form-select"}),
            "date_validite": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


QuoteLineFormSet = inlineformset_factory(
    Quote, QuoteLine,
    fields=["type_frais", "designation", "quantite", "prix_unitaire"],
    widgets=LINE_WIDGETS,
    extra=1, can_delete=True,
)


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["dossier", "client", "statut", "date_echeance", "notes"]
        widgets = {
            "dossier": forms.Select(attrs={"class": "form-select"}),
            "client": forms.Select(attrs={"class": "form-select"}),
            "statut": forms.Select(attrs={"class": "form-select"}),
            "date_echeance": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


InvoiceLineFormSet = inlineformset_factory(
    Invoice, InvoiceLine,
    fields=["type_frais", "designation", "quantite", "prix_unitaire"],
    widgets=LINE_WIDGETS,
    extra=1, can_delete=True,
)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["montant", "date_paiement", "mode_paiement", "reference", "notes"]
        widgets = {
            "montant": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "date_paiement": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "mode_paiement": forms.Select(attrs={"class": "form-select"}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }


class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ["type_relance", "date_relance", "notes"]
        widgets = {
            "type_relance": forms.Select(attrs={"class": "form-select"}),
            "date_relance": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
