"""Client portal: read-only views scoped to the logged-in client's company.

Every queryset goes through ClientPortalMixin's helpers, which filter on
request.user.partner, so a client can never reach another client's data (they get a 404).
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from billing.models import Invoice, Quote, StatutDevis, StatutFacture
from billing.quote_response import ReponseImpossible, repondre_devis
from billing.views import PDF_QUERYSETS, invoice_pdf_response, quote_pdf_response
from core.files import serve_file
from core.models import Societe
from documents.models import Document
from dossiers.models import Dossier, StatutDossier

from .forms import ReponseDevisForm

FACTURES_MASQUEES = (StatutFacture.BROUILLON, StatutFacture.ANNULEE)
DEVIS_MASQUES = (StatutDevis.BROUILLON,)


class ClientPortalMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_client_portal or not request.user.partner_id:
            raise PermissionDenied
        self.partner = request.user.partner
        return super().dispatch(request, *args, **kwargs)

    def dossiers(self):
        return Dossier.objects.filter(client=self.partner)

    def factures(self, qs=None):
        qs = qs if qs is not None else Invoice.objects.all()
        return qs.filter(client=self.partner).exclude(statut__in=FACTURES_MASQUEES)

    def devis(self, qs=None):
        qs = qs if qs is not None else Quote.objects.all()
        return qs.filter(client=self.partner).exclude(statut__in=DEVIS_MASQUES)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["partner"] = self.partner
        ctx["societe"] = Societe.load()
        return ctx


class HomeView(ClientPortalMixin, TemplateView):
    template_name = "portal/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dossiers = self.dossiers()
        en_cours = dossiers.exclude(statut__in=[StatutDossier.CLOTURE, StatutDossier.ANNULE])
        factures = self.factures(Invoice.objects.prefetch_related("lignes", "paiements"))
        a_regler = [f for f in factures if f.solde > 0]
        ctx.update({
            "nb_en_cours": en_cours.count(),
            "nb_en_douane": en_cours.filter(statut=StatutDossier.EN_DOUANE).count(),
            "factures_a_regler": a_regler,
            "solde_du": sum((f.solde for f in a_regler), 0),
            "dossiers_recents": en_cours.order_by("-updated_at")[:6],
            "devis_a_valider": [
                q for q in self.devis(Quote.objects.filter(statut=StatutDevis.ENVOYE).prefetch_related("lignes"))
                if q.peut_repondre_client
            ],
        })
        return ctx


class DossierListView(ClientPortalMixin, ListView):
    template_name = "portal/dossier_list.html"
    context_object_name = "dossiers"
    paginate_by = 20

    def get_queryset(self):
        qs = self.dossiers()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(reference__icontains=q) | Q(reference_client__icontains=q))
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class DossierDetailView(ClientPortalMixin, DetailView):
    template_name = "portal/dossier_detail.html"
    context_object_name = "dossier"

    def get_queryset(self):
        return self.dossiers()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dossier = self.object
        ctx.update({
            "evenements": dossier.evenements.filter(visible_client=True),
            "marchandises": dossier.marchandises.all(),
            "documents": dossier.documents.all(),
            "factures": self.factures(dossier.factures.prefetch_related("lignes", "paiements")),
            "devis": self.devis(dossier.devis.prefetch_related("lignes")),
        })
        return ctx


class DocumentDownloadView(ClientPortalMixin, View):
    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk, dossier__client=self.partner)
        return serve_file(document.fichier, document.filename(), as_attachment=True)


class InvoiceListView(ClientPortalMixin, ListView):
    template_name = "portal/invoice_list.html"
    context_object_name = "factures"
    paginate_by = 20

    def get_queryset(self):
        return self.factures(
            Invoice.objects.select_related("dossier").prefetch_related("lignes", "paiements")
        )


class QuoteListView(ClientPortalMixin, ListView):
    template_name = "portal/quote_list.html"
    context_object_name = "devis"
    paginate_by = 20

    def get_queryset(self):
        return self.devis(Quote.objects.select_related("dossier").prefetch_related("lignes"))


class QuoteDetailView(ClientPortalMixin, DetailView):
    """Quote summary; a POST records the client's acceptance or refusal."""

    template_name = "portal/quote_detail.html"
    context_object_name = "quote"

    def get_queryset(self):
        return self.devis(Quote.objects.select_related("dossier").prefetch_related("lignes"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("form", ReponseDevisForm(initial={"nom": self.request.user.get_full_name()}))
        return ctx

    def post(self, request, pk):
        self.object = self.get_object()
        form = ReponseDevisForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        accepte = form.cleaned_data["decision"] == "accepter"
        try:
            repondre_devis(
                request, self.object.pk, self.partner, accepte,
                form.cleaned_data["nom"], form.cleaned_data["commentaire"],
            )
        except ReponseImpossible as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                "Merci, votre accord a bien été enregistré. Nous lançons l'opération."
                if accepte else "Votre refus a bien été enregistré. Nous reviendrons vers vous.",
            )
        return redirect("portal:quote_detail", pk=self.object.pk)


class InvoicePdfView(ClientPortalMixin, View):
    def get(self, request, pk):
        invoice = get_object_or_404(self.factures(PDF_QUERYSETS["invoice"]()), pk=pk)
        return invoice_pdf_response(invoice, download=bool(request.GET.get("download")))


class QuotePdfView(ClientPortalMixin, View):
    def get(self, request, pk):
        quote = get_object_or_404(self.devis(PDF_QUERYSETS["quote"]()), pk=pk)
        return quote_pdf_response(quote, download=bool(request.GET.get("download")))
