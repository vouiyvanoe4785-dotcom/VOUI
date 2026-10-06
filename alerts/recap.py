"""Daily e-mail digest of the alerts that concern each staff member."""
from collections import OrderedDict

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.models import Role, User
from core.models import Societe

from .services import Categorie, collect_alertes

CATEGORIES_FINANCIERES = {Categorie.FACTURE_ECHUE, Categorie.ACHAT, Categorie.REPONSE_DEVIS}
TOUJOURS = {Categorie.VALIDATION}  # already filtered by role in collect_alertes


def alertes_pour(user):
    """The alerts a user should receive: everything for management, money matters for
    accounting, and otherwise the user's own dossiers plus validations for their role."""
    alertes = collect_alertes(user)
    if user.is_superuser or user.role in (Role.ADMIN, Role.DIRECTION):
        return alertes
    categories = TOUJOURS | (CATEGORIES_FINANCIERES if user.role == Role.COMPTABLE else set())
    return [a for a in alertes if a.categorie in categories or a.agent_id == user.pk]


def destinataires():
    return (
        User.objects.filter(is_active=True, recap_alertes_email=True)
        .exclude(email="")
        .exclude(role__in=[Role.CLIENT, Role.CONSULTATION])
        .order_by("username")
    )


def construire_email(user, alertes):
    groupes = OrderedDict()
    for alerte in alertes:
        groupes.setdefault(alerte.categorie_label, []).append(alerte)
    urgentes = sum(1 for a in alertes if a.niveau == "danger")
    societe = Societe.load()
    sujet = (
        f"[{societe.raison_sociale}] {len(alertes)} alerte{'s' if len(alertes) > 1 else ''}"
        + (f" dont {urgentes} urgente{'s' if urgentes > 1 else ''}" if urgentes else "")
        + f" - {timezone.localdate():%d/%m/%Y}"
    )
    corps = render_to_string("alerts/emails/recap.txt", {
        "user": user, "groupes": groupes, "site_url": settings.SITE_URL, "societe": societe,
    })
    return sujet, corps


def envoyer_recap(users=None, dry_run=False):
    """Returns [(user, number of alerts)] for the users who got (or would get) an e-mail."""
    envoyes = []
    for user in users if users is not None else destinataires():
        alertes = alertes_pour(user)
        if not alertes:
            continue
        sujet, corps = construire_email(user, alertes)
        if not dry_run:
            send_mail(sujet, corps, None, [user.email])
        envoyes.append((user, len(alertes)))
    return envoyes
