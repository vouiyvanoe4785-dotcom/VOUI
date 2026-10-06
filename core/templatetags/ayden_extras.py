from django import template

register = template.Library()

STATUS_COLORS = {
    # Dossiers
    "ouvert": "primary",
    "en_cours": "info",
    "en_douane": "warning",
    "livre": "teal",
    "cloture": "secondary",
    "annule": "danger",
    # Devis
    "brouillon": "secondary",
    "envoye": "info",
    "envoyee": "info",
    "accepte": "success",
    "refuse": "danger",
    "expire": "secondary",
    # Factures
    "payee_partiel": "warning",
    "payee": "success",
    "en_retard": "danger",
    "annulee": "danger",
    # Achats fournisseurs
    "recue": "info",
    "validee": "primary",
    "contestee": "danger",
    # Étapes de validation
    "en_attente": "secondary",
    "approuvee": "success",
    "refusee": "danger",
}


@register.filter
def status_color(value):
    return STATUS_COLORS.get(value, "secondary")


@register.filter
def can_act(step, user):
    if not getattr(user, "is_authenticated", False):
        return False
    if step.statut != "en_attente" or step.is_bloquee:
        return False
    return user.is_admin_role() or user.role == step.role_requis


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return ""
    return mapping.get(key, key)


@register.filter
def mul(value, arg):
    try:
        return value * arg
    except TypeError:
        return ""


@register.filter
def can_delete_event(event, user):
    return event.can_delete(user)
