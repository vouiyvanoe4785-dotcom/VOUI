from collections import OrderedDict
from decimal import Decimal

from billing.models import Invoice, StatutFacture
from dossiers.models import Dossier
from purchasing.models import StatutAchat, SupplierInvoice

NON_AFFECTE = "Non affecté"


def _service_key(agent):
    if agent and agent.service:
        return agent.service
    return NON_AFFECTE


def get_available_services():
    services = (
        Dossier.objects.exclude(agent_responsable__service="")
        .exclude(agent_responsable__isnull=True)
        .values_list("agent_responsable__service", flat=True)
        .distinct()
        .order_by("agent_responsable__service")
    )
    return list(services)


def build_report(date_debut, date_fin, service=None):
    dossiers_qs = Dossier.objects.filter(
        date_ouverture__gte=date_debut, date_ouverture__lte=date_fin
    ).select_related("agent_responsable")

    invoices_qs = (
        Invoice.objects.exclude(statut=StatutFacture.ANNULEE)
        .filter(date_emission__gte=date_debut, date_emission__lte=date_fin)
        .select_related("dossier__agent_responsable")
        .prefetch_related("lignes", "paiements")
    )

    achats_qs = (
        SupplierInvoice.objects.exclude(statut=StatutAchat.ANNULEE)
        .filter(date_facture__gte=date_debut, date_facture__lte=date_fin)
        .select_related("dossier__agent_responsable")
        .prefetch_related("lignes", "paiements")
    )

    if service:
        dossiers_qs = dossiers_qs.filter(agent_responsable__service=service)
        invoices_qs = invoices_qs.filter(dossier__agent_responsable__service=service)
        achats_qs = achats_qs.filter(dossier__agent_responsable__service=service)

    rows = OrderedDict()

    def get_row(key):
        if key not in rows:
            rows[key] = {
                "service": key,
                "nb_dossiers": 0,
                "ca_facture": Decimal("0"),
                "ca_encaisse": Decimal("0"),
                "depenses_engagees": Decimal("0"),
                "depenses_payees": Decimal("0"),
            }
        return rows[key]

    for dossier in dossiers_qs:
        get_row(_service_key(dossier.agent_responsable))["nb_dossiers"] += 1

    for invoice in invoices_qs:
        agent = invoice.dossier.agent_responsable if invoice.dossier else None
        row = get_row(_service_key(agent))
        row["ca_facture"] += invoice.montant_total
        row["ca_encaisse"] += invoice.montant_paye

    for achat in achats_qs:
        agent = achat.dossier.agent_responsable if achat.dossier else None
        row = get_row(_service_key(agent))
        row["depenses_engagees"] += achat.montant_total
        row["depenses_payees"] += achat.montant_paye

    for row in rows.values():
        row["resultat"] = row["ca_encaisse"] - row["depenses_payees"]

    ordered_rows = sorted(rows.values(), key=lambda r: r["service"])

    totaux = {
        "nb_dossiers": sum(r["nb_dossiers"] for r in ordered_rows),
        "ca_facture": sum((r["ca_facture"] for r in ordered_rows), Decimal("0")),
        "ca_encaisse": sum((r["ca_encaisse"] for r in ordered_rows), Decimal("0")),
        "depenses_engagees": sum((r["depenses_engagees"] for r in ordered_rows), Decimal("0")),
        "depenses_payees": sum((r["depenses_payees"] for r in ordered_rows), Decimal("0")),
    }
    totaux["resultat"] = totaux["ca_encaisse"] - totaux["depenses_payees"]

    return ordered_rows, totaux
