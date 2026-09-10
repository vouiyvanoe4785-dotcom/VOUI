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
}


@register.filter
def status_color(value):
    return STATUS_COLORS.get(value, "secondary")


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
