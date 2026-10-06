"""A client accepting or refusing a quote from the portal."""
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from tracking.models import DossierEvent, TypeEvenement

from .models import Quote, StatutDevis


class ReponseImpossible(Exception):
    pass


def repondre_devis(request, quote_pk, partner, accepte, nom, commentaire=""):
    """Record the client's answer once; raises ReponseImpossible if it can no longer be given."""
    with transaction.atomic():
        # Lock the row: a double click or two open tabs must not answer twice.
        quote = Quote.objects.select_for_update().select_related("dossier").get(pk=quote_pk, client=partner)
        if not quote.peut_repondre_client:
            raise ReponseImpossible(
                "Ce devis a expiré." if quote.est_expire else "Une réponse a déjà été donnée pour ce devis."
            )
        quote.statut = StatutDevis.ACCEPTE if accepte else StatutDevis.REFUSE
        quote.reponse_client_le = timezone.now()
        quote.reponse_client_par = request.user
        quote.reponse_client_nom = nom.strip()
        quote.reponse_client_commentaire = commentaire.strip()
        quote.save(update_fields=[
            "statut", "reponse_client_le", "reponse_client_par", "reponse_client_nom",
            "reponse_client_commentaire", "updated_at",
        ])
        if quote.dossier:
            texte = f"{quote.get_type_devis_display()} {quote.reference} {'accepté' if accepte else 'refusé'} par {quote.reponse_client_nom}."
            if quote.reponse_client_commentaire:
                texte += f"\n« {quote.reponse_client_commentaire} »"
            DossierEvent.objects.create(
                dossier=quote.dossier,
                type_evenement=TypeEvenement.DEVIS_ACCEPTE if accepte else TypeEvenement.DEVIS_REFUSE,
                commentaire=texte, created_by=request.user, visible_client=True,
            )
        transaction.on_commit(lambda: _notifier_equipe(request, quote))
    return quote


def destinataires(quote):
    users = [quote.created_by]
    if quote.dossier and quote.dossier.agent_responsable:
        users.append(quote.dossier.agent_responsable)
    return sorted({u.email for u in users if u and u.is_active and u.email})


def _notifier_equipe(request, quote):
    to = destinataires(quote)
    if not to:
        return
    ctx = {"quote": quote, "url": request.build_absolute_uri(quote.get_absolute_url())}
    sujet = f"{quote.client} a {'accepté' if quote.statut == StatutDevis.ACCEPTE else 'refusé'} le devis {quote.reference}"
    # The answer is already saved; a mail server hiccup must not turn it into an error page.
    send_mail(sujet, render_to_string("billing/emails/reponse_devis.txt", ctx), None, to, fail_silently=True)
