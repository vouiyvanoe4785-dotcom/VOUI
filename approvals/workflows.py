from django.contrib.contenttypes.models import ContentType

from accounts.models import Role

from .models import ValidationStep

WORKFLOWS = {
    "dossiers.dossier": [
        (1, "Contrôle des documents et des informations", Role.COMPTABLE),
        (2, "Validation direction", Role.DIRECTION),
    ],
    "billing.invoice": [
        (1, "Validation avant envoi au client", Role.DIRECTION),
    ],
}


def get_workflow_key(obj):
    ct = ContentType.objects.get_for_model(obj)
    return f"{ct.app_label}.{ct.model}", ct


def get_steps(obj):
    _, ct = get_workflow_key(obj)
    return list(
        ValidationStep.objects.filter(content_type=ct, object_id=obj.pk)
        .select_related("validateur")
    )


def has_workflow_config(obj):
    key, _ = get_workflow_key(obj)
    return key in WORKFLOWS


def ensure_workflow(obj):
    key, ct = get_workflow_key(obj)
    config = WORKFLOWS.get(key)
    if not config:
        return []
    existing = ValidationStep.objects.filter(content_type=ct, object_id=obj.pk)
    if existing.exists():
        return list(existing)
    steps = [
        ValidationStep(content_type=ct, object_id=obj.pk, ordre=ordre, libelle=libelle, role_requis=role)
        for ordre, libelle, role in config
    ]
    ValidationStep.objects.bulk_create(steps)
    return get_steps(obj)
