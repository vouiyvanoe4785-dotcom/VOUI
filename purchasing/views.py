from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView

from core.document_forms import save_document_with_lines
from dossiers.models import Dossier

from .forms import SupplierInvoiceForm, SupplierInvoiceLineFormSet, SupplierPaymentForm
from .models import StatutAchat, SupplierInvoice


class SupplierInvoiceListView(LoginRequiredMixin, ListView):
    model = SupplierInvoice
    template_name = "purchasing/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        qs = SupplierInvoice.objects.select_related("fournisseur", "dossier")
        statut = self.request.GET.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuts"] = StatutAchat.choices
        ctx["current_statut"] = self.request.GET.get("statut", "")
        return ctx


class SupplierInvoiceDetailView(LoginRequiredMixin, DetailView):
    model = SupplierInvoice
    template_name = "purchasing/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["payment_form"] = SupplierPaymentForm()
        return ctx


class SupplierInvoiceEditView(LoginRequiredMixin, View):
    template_name = "purchasing/invoice_form.html"

    def get_instance(self, pk):
        return get_object_or_404(SupplierInvoice, pk=pk) if pk else None

    def get(self, request, pk=None):
        instance = self.get_instance(pk)
        initial = {}
        if not instance and request.GET.get("dossier"):
            dossier = get_object_or_404(Dossier, pk=request.GET["dossier"])
            initial = {"dossier": dossier.pk}
        form = SupplierInvoiceForm(instance=instance, initial=initial)
        formset = SupplierInvoiceLineFormSet(instance=instance)
        return render(request, self.template_name, {"form": form, "formset": formset, "object": instance})

    def post(self, request, pk=None):
        instance = self.get_instance(pk)
        form = SupplierInvoiceForm(request.POST, instance=instance)
        invoice, formset = save_document_with_lines(request, form, SupplierInvoiceLineFormSet)
        if invoice is not None:
            messages.success(request, "Achat / facture fournisseur enregistré avec succès.")
            return redirect("purchasing:invoice_detail", pk=invoice.pk)
        return render(request, self.template_name, {"form": form, "formset": formset, "object": instance})


class SupplierInvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = SupplierInvoice

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Achat / facture fournisseur supprimé.")
        return redirect("purchasing:invoice_list")


class SupplierPaymentCreateView(LoginRequiredMixin, View):
    def post(self, request, invoice_pk):
        invoice = get_object_or_404(SupplierInvoice, pk=invoice_pk)
        if not request.user.can_manage_billing():
            messages.error(request, "Vous n'êtes pas autorisé à enregistrer un paiement.")
            return redirect("purchasing:invoice_detail", pk=invoice_pk)
        form = SupplierPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.created_by = request.user
            payment.save()
            if payment.compte:
                from treasury.models import CashTransaction, TypeMouvement

                CashTransaction.objects.create(
                    compte=payment.compte,
                    type_mouvement=TypeMouvement.SORTIE,
                    categorie="paiement_fournisseur",
                    montant=payment.montant,
                    date_mouvement=payment.date_paiement,
                    description=f"Paiement achat {invoice.reference} - {invoice.fournisseur}",
                    dossier=invoice.dossier,
                    tiers=invoice.fournisseur,
                    related_supplier_payment=payment,
                    created_by=request.user,
                )
            if invoice.solde <= 0:
                invoice.statut = StatutAchat.PAYEE
            else:
                invoice.statut = StatutAchat.PAYEE_PARTIEL
            invoice.save(update_fields=["statut"])
            messages.success(request, "Paiement fournisseur enregistré.")
        else:
            messages.error(request, "Erreur dans le formulaire de paiement.")
        return redirect("purchasing:invoice_detail", pk=invoice_pk)
