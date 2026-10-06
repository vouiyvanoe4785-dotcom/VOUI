"""Alerts are computed on the fly from the current data: nothing is stored, so an
alert disappears as soon as its cause is fixed (invoice paid, event logged...)."""
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db.models import Max, OuterRef, Subquery
from django.utils import timezone

from accounts.models import Role
from approvals.models import EtapeStatut, ValidationStep
from billing.models import Invoice, Quote, StatutDevis, StatutFacture
from dossiers.models import Dossier, StatutDossier
from purchasing.models import StatutAchat, SupplierInvoice
from tracking.models import DossierEvent, TypeEvenement


class Categorie:
    FACTURE_ECHUE = "facture_echue"
    INCIDENT = "incident"
    DOSSIER_INACTIF = "dossier_inactif"
    DEVIS = "devis"
    ACHAT = "achat"
    VALIDATION = "validation"

    LABELS = {
        FACTURE_ECHUE: "Factures échues",
        INCIDENT: "Incidents ouverts",
        DOSSIER_INACTIF: "Dossiers sans activité",
        DEVIS: "Devis à relancer",
        ACHAT: "Fournisseurs à payer",
        VALIDATION: "Validations à faire",
    }
    ICONS = {
        FACTURE_ECHUE: "receipt",
        INCIDENT: "exclamation-triangle",
        DOSSIER_INACTIF: "hourglass-split",
        DEVIS: "file-earmark-text",
        ACHAT: "bag",
        VALIDATION: "pen",
    }


NIVEAU_ORDRE = {"danger": 0, "warning": 1, "info": 2}
DOSSIERS_ACTIFS = (StatutDossier.OUVERT, StatutDossier.EN_COURS, StatutDossier.EN_DOUANE)


@dataclass
class Alerte:
    categorie: str
    niveau: str  # danger / warning / info (Bootstrap colours)
    titre: str
    detail: str
    url: str
    jours: int = 0  # how overdue / idle, used to sort within a level
    agent_id: int | None = field(default=None, repr=False)

    @property
    def categorie_label(self):
        return Categorie.LABELS[self.categorie]

    @property
    def icon(self):
        return Categorie.ICONS[self.categorie]


def _montant(value):
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + f" {settings.DEFAULT_CURRENCY}"


def _jours(n):
    return f"{n} jour{'s' if n > 1 else ''}"


def _factures_echues(today):
    critique = settings.ALERTE_FACTURE_RETARD_CRITIQUE_JOURS
    qs = (
        Invoice.objects.filter(date_echeance__lt=today)
        .exclude(statut__in=[StatutFacture.ANNULEE, StatutFacture.BROUILLON, StatutFacture.PAYEE])
        .select_related("client", "dossier")
        .prefetch_related("lignes", "paiements")
    )
    for invoice in qs:
        solde = invoice.solde
        if solde <= 0:
            continue
        retard = (today - invoice.date_echeance).days
        yield Alerte(
            Categorie.FACTURE_ECHUE, "danger" if retard >= critique else "warning",
            f"{invoice.reference} - {invoice.client}",
            f"Échue depuis {_jours(retard)} · reste {_montant(solde)}",
            invoice.get_absolute_url(), retard,
            invoice.dossier.agent_responsable_id if invoice.dossier else None,
        )


def _dossiers(now):
    seuil = settings.ALERTE_DOSSIER_INACTIF_JOURS
    dernier = DossierEvent.objects.filter(dossier=OuterRef("pk")).order_by("-date_evenement", "-created_at")
    qs = Dossier.objects.filter(statut__in=DOSSIERS_ACTIFS).select_related("client").annotate(
        derniere_activite=Max("evenements__date_evenement"),
        dernier_type=Subquery(dernier.values("type_evenement")[:1]),
        dernier_commentaire=Subquery(dernier.values("commentaire")[:1]),
    )
    for dossier in qs:
        url = dossier.get_absolute_url() + "#suivi"
        if dossier.dernier_type == TypeEvenement.INCIDENT:
            yield Alerte(
                Categorie.INCIDENT, "danger", f"{dossier.reference} - {dossier.client}",
                (dossier.dernier_commentaire or "Incident signalé")[:140],
                url, (now - dossier.derniere_activite).days, dossier.agent_responsable_id,
            )
            continue
        derniere = max(filter(None, [dossier.derniere_activite, dossier.updated_at]))
        inactif = (now - derniere).days
        if inactif >= seuil:
            yield Alerte(
                Categorie.DOSSIER_INACTIF, "warning", f"{dossier.reference} - {dossier.client}",
                f"Aucune activité depuis {_jours(inactif)} ({dossier.get_statut_display().lower()})",
                url, inactif, dossier.agent_responsable_id,
            )


def _devis(today):
    proche = settings.ALERTE_ECHEANCE_PROCHE_JOURS
    qs = Quote.objects.filter(
        statut=StatutDevis.ENVOYE, date_validite__lte=today + timedelta(days=proche)
    ).select_related("client", "dossier")
    for quote in qs:
        ecart = (quote.date_validite - today).days
        if ecart < 0:
            niveau, detail = "warning", f"Expiré depuis {_jours(-ecart)} sans réponse du client"
        else:
            niveau = "info"
            detail = "Expire aujourd'hui" if ecart == 0 else f"Expire dans {_jours(ecart)}"
        yield Alerte(
            Categorie.DEVIS, niveau, f"{quote.reference} - {quote.client}", detail,
            quote.get_absolute_url(), -ecart,
            quote.dossier.agent_responsable_id if quote.dossier else None,
        )


def _achats(today):
    proche = settings.ALERTE_ECHEANCE_PROCHE_JOURS
    qs = (
        SupplierInvoice.objects.filter(date_echeance__lte=today + timedelta(days=proche))
        .exclude(statut__in=[
            StatutAchat.BROUILLON, StatutAchat.PAYEE, StatutAchat.CONTESTEE, StatutAchat.ANNULEE,
        ])
        .select_related("fournisseur", "dossier")
        .prefetch_related("lignes", "paiements")
    )
    for achat in qs:
        solde = achat.solde
        if solde <= 0:
            continue
        ecart = (achat.date_echeance - today).days
        if ecart < 0:
            niveau, quand = "warning", f"Échue depuis {_jours(-ecart)}"
        else:
            niveau = "info"
            quand = "Échéance aujourd'hui" if ecart == 0 else f"Échéance dans {_jours(ecart)}"
        yield Alerte(
            Categorie.ACHAT, niveau, f"{achat.reference} - {achat.fournisseur}",
            f"{quand} · reste {_montant(solde)}", achat.get_absolute_url(), -ecart,
            achat.dossier.agent_responsable_id if achat.dossier else None,
        )


def _validations(user):
    qs = ValidationStep.objects.filter(statut=EtapeStatut.EN_ATTENTE).select_related("content_type")
    if not user.is_admin_role():
        qs = qs.filter(role_requis=user.role)
    for step in qs:
        obj = step.content_object
        if obj is None or step.is_bloquee:
            continue
        yield Alerte(
            Categorie.VALIDATION, "info", str(obj), step.libelle,
            obj.get_absolute_url(), 0, user.pk,
        )


def collect_alertes(user, now=None):
    now = now or timezone.now()
    today = timezone.localdate(now)
    sources = [_factures_echues(today), _dossiers(now), _devis(today)]
    if user.can_manage_billing():
        sources.append(_achats(today))
    if user.role != Role.CONSULTATION:
        sources.append(_validations(user))
    alertes = [a for source in sources for a in source]
    alertes.sort(key=lambda a: (NIVEAU_ORDRE[a.niveau], -a.jours))
    return alertes
