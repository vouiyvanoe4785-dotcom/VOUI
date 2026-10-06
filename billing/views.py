from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView

from approvals.workflows import get_steps
from core.pdf import pdf_response
from dossiers.models import Dossier

from .forms import (
    InvoiceForm, InvoiceLineFormSet, PaymentForm, QuoteForm, QuoteLineFormSet, ReminderForm,
)
from .models import Invoice, Payment, Quote, Reminder, StatutFacture, TypeDevis


class QuoteListView(LoginRequiredMixin, ListView):
    model = Quote
    template_name = "billing/quote_list.html"
    context_object_name = "quotes"
    paginate_by = 20

    def get_queryset(self):
        return Quote.objects.select_related("client", "dossier")


class QuoteDetailView(LoginRequiredMixin, DetailView):
    model = Quote
    template_name = "billing/quote_detail.html"
    context_object_name = "quote"


class QuoteEditView(LoginRequiredMixin, View):
    template_name = "billing/quote_form.html"

    def get_instance(self, pk):
        return get_object_or_404(Quote, pk=pk) if pk else None

    def get(self, request, pk=None):
        instance = self.get_instance(pk)
        initial = {}
        if not instance and request.GET.get("dossier"):
            dossier = get_object_or_404(Dossier, pk=request.GET["dossier"])
            initial = {"dossier": dossier.pk, "client": dossier.client.pk}
        form = QuoteForm(instance=instance, initial=initial)
        formset = QuoteLineFormSet(instance=instance)
        return render(request, self.template_name, {"form": form, "formset": formset, "object": instance})

    def post(self, request, pk=None):
        instance = self.get_instance(pk)
        form = QuoteForm(request.POST, instance=instance)
        formset_instance = instance or Quote()
        if form.is_valid():
            quote = form.save(commit=False)
            if not quote.created_by_id:
                quote.created_by = request.user
            quote.save()
            formset = QuoteLineFormSet(request.POST, instance=quote)
            if formset.is_valid():
                formset.save()
                messages.success(request, "Devis enregistré avec succès.")
                return redirect("billing:quote_detail", pk=quote.pk)
        else:
            formset = QuoteLineFormSet(request.POST, instance=formset_instance)
        return render(request, self.template_name, {"form": form, "formset": formset, "object": instance})


class QuoteDeleteView(LoginRequiredMixin, DeleteView):
    model = Quote
    success_url = "/devis/"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Devis supprimé.")
        return redirect("billing:quote_list")


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "billing/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        qs = Invoice.objects.select_related("client", "dossier")
        statut = self.request.GET.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuts"] = StatutFacture.choices
        ctx["current_statut"] = self.request.GET.get("statut", "")
        return ctx


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "billing/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["payment_form"] = PaymentForm()
        ctx["reminder_form"] = ReminderForm()
        ctx["validation_steps"] = get_steps(self.object)
        ctx["validation_ct_id"] = ContentType.objects.get_for_model(Invoice).id
        ctx["validation_object_id"] = self.object.pk
        return ctx


class InvoiceEditView(LoginRequiredMixin, View):
    template_name = "billing/invoice_form.html"

    def get_instance(self, pk):
        return get_object_or_404(Invoice, pk=pk) if pk else None

    def get(self, request, pk=None):
        instance = self.get_instance(pk)
        initial = {}
        if not instance and request.GET.get("dossier"):
            dossier = get_object_or_404(Dossier, pk=request.GET["dossier"])
            initial = {"dossier": dossier.pk, "client": dossier.client.pk}
        form = InvoiceForm(instance=instance, initial=initial)
        formset = InvoiceLineFormSet(instance=instance)
        return render(request, self.template_name, {"form": form, "formset": formset, "object": instance})

    def post(self, request, pk=None):
        instance = self.get_instance(pk)
        form = InvoiceForm(request.POST, instance=instance)
        formset_instance = instance or Invoice()
        if form.is_valid():
            invoice = form.save(commit=False)
            if not invoice.created_by_id:
                invoice.created_by = request.user
            invoice.save()
            formset = InvoiceLineFormSet(request.POST, instance=invoice)
            if formset.is_valid():
                formset.save()
                messages.success(request, "Facture enregistrée avec succès.")
                return redirect("billing:invoice_detail", pk=invoice.pk)
        else:
            formset = InvoiceLineFormSet(request.POST, instance=formset_instance)
        return render(request, self.template_name, {"form": form, "formset": formset, "object": instance})


class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Invoice

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, "Facture supprimée.")
        return redirect("billing:invoice_list")


class PaymentCreateView(LoginRequiredMixin, View):
    def post(self, request, invoice_pk):
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
        if not request.user.can_manage_billing():
            messages.error(request, "Vous n'êtes pas autorisé à enregistrer un paiement.")
            return redirect("billing:invoice_detail", pk=invoice_pk)
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.created_by = request.user
            payment.save()
            if payment.compte:
                from treasury.models import CashTransaction, TypeMouvement

                CashTransaction.objects.create(
                    compte=payment.compte,
                    type_mouvement=TypeMouvement.ENTREE,
                    categorie="encaissement_client",
                    montant=payment.montant,
                    date_mouvement=payment.date_paiement,
                    description=f"Encaissement facture {invoice.reference} - {invoice.client}",
                    dossier=invoice.dossier,
                    tiers=invoice.client,
                    related_payment=payment,
                    created_by=request.user,
                )
            if invoice.solde <= 0:
                invoice.statut = StatutFacture.PAYEE
            else:
                invoice.statut = StatutFacture.PAYEE_PARTIEL
            invoice.save(update_fields=["statut"])
            messages.success(request, "Paiement enregistré.")
        else:
            messages.error(request, "Erreur dans le formulaire de paiement.")
        return redirect("billing:invoice_detail", pk=invoice_pk)


class ReminderCreateView(LoginRequiredMixin, View):
    def post(self, request, invoice_pk):
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.invoice = invoice
            reminder.created_by = request.user
            reminder.save()
            messages.success(request, "Relance enregistrée.")
        else:
            messages.error(request, "Erreur dans le formulaire de relance.")
        return redirect("billing:invoice_detail", pk=invoice_pk)


def _document_context(doc, lignes):
    from core.amounts import montant_en_lettres
    from core.models import Societe

    devise = settings.DEFAULT_CURRENCY
    totaux = {}
    for line in lignes:
        label = line.get_type_frais_display()
        totaux[label] = totaux.get(label, 0) + line.montant
    total = sum((line.montant for line in lignes), Decimal("0"))
    return {
        "doc": doc,
        "societe": Societe.load(),
        "client": doc.client,
        "dossier": doc.dossier,
        "lignes": lignes,
        "sous_totaux": list(totaux.items()),
        "total": total,
        "total_lettres": montant_en_lettres(total, devise),
        "devise": devise,
    }


class QuotePdfView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quote = get_object_or_404(Quote.objects.select_related("client", "dossier"), pk=pk)
        ctx = _document_context(quote, list(quote.lignes.all()))
        infos = [("Date", quote.date_creation.strftime("%d/%m/%Y"))]
        if quote.date_validite:
            infos.append(("Valable jusqu'au", quote.date_validite.strftime("%d/%m/%Y")))
        ctx.update({
            "titre": quote.get_type_devis_display(),
            "infos": infos,
            "phrase_montant": f"Arrêté{'e' if quote.type_devis == TypeDevis.PROFORMA else ''} "
                              f"{'la présente facture proforma' if quote.type_devis == TypeDevis.PROFORMA else 'le présent devis'} "
                              "à la somme de :",
            "mentions": ctx["societe"].mentions_devis,
        })
        return pdf_response(
            "billing/pdf/document.html", ctx, f"{quote.reference}.pdf",
            download=bool(request.GET.get("download")),
        )


class InvoicePdfView(LoginRequiredMixin, View):
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice.objects.select_related("client", "dossier"), pk=pk)
        ctx = _document_context(invoice, list(invoice.lignes.all()))
        paiements = list(invoice.paiements.all())
        paye = sum((p.montant for p in paiements), Decimal("0"))
        infos = [("Date d'émission", invoice.date_emission.strftime("%d/%m/%Y"))]
        if invoice.date_echeance:
            infos.append(("Échéance", invoice.date_echeance.strftime("%d/%m/%Y")))
        ctx.update({
            "titre": "Facture",
            "infos": infos,
            "phrase_montant": "Arrêtée la présente facture à la somme de :",
            "note_label": "Note de détail",
            "mentions": ctx["societe"].mentions_facture,
            "afficher_reglements": paye > 0,
            "paiements": paiements,
            "paye": paye,
            "solde": ctx["total"] - paye,
        })
        return pdf_response(
            "billing/pdf/document.html", ctx, f"{invoice.reference}.pdf",
            download=bool(request.GET.get("download")),
        )
