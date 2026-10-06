from django import forms
from django.forms import inlineformset_factory

from billing.forms import LINE_FIELDS, LINE_WIDGETS
from partners.models import PartnerType

from .models import SupplierInvoice, SupplierInvoiceLine, SupplierPayment



class SupplierInvoiceForm(forms.ModelForm):
    class Meta:
        model = SupplierInvoice
        fields = [
            "fournisseur", "dossier", "reference_fournisseur", "statut",
            "date_facture", "date_echeance", "notes",
        ]
        widgets = {
            "fournisseur": forms.Select(attrs={"class": "form-select"}),
            "dossier": forms.Select(attrs={"class": "form-select"}),
            "reference_fournisseur": forms.TextInput(attrs={"class": "form-control"}),
            "statut": forms.Select(attrs={"class": "form-select"}),
            "date_facture": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "date_echeance": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fournisseur"].queryset = self.fields["fournisseur"].queryset.filter(
            type_tiers__in=[
                PartnerType.FOURNISSEUR, PartnerType.PRESTATAIRE,
                PartnerType.TRANSPORTEUR, PartnerType.DOUANE,
            ]
        )


SupplierInvoiceLineFormSet = inlineformset_factory(
    SupplierInvoice, SupplierInvoiceLine,
    fields=LINE_FIELDS,
    widgets=LINE_WIDGETS,
    extra=1, can_delete=True,
)


class SupplierPaymentForm(forms.ModelForm):
    class Meta:
        model = SupplierPayment
        fields = ["montant", "date_paiement", "mode_paiement", "reference", "compte", "notes"]
        widgets = {
            "montant": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "date_paiement": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "mode_paiement": forms.Select(attrs={"class": "form-select"}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "compte": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from treasury.models import CashAccount

        self.fields["compte"].queryset = CashAccount.objects.filter(is_active=True)
        self.fields["compte"].required = False
        self.fields["compte"].empty_label = "— Non décaissé d'une caisse —"
