from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View

from .models import EtapeStatut, ValidationStep
from .workflows import ensure_workflow


def _redirect_target(request, obj):
    if obj is not None and hasattr(obj, "get_absolute_url"):
        return obj.get_absolute_url()
    return request.META.get("HTTP_REFERER", "/")


class StartValidationView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, object_id):
        ct = get_object_or_404(ContentType, pk=content_type_id)
        obj = get_object_or_404(ct.model_class(), pk=object_id)
        ensure_workflow(obj)
        messages.success(request, "Circuit de validation démarré.")
        return redirect(_redirect_target(request, obj))


class ValidationActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        step = get_object_or_404(ValidationStep, pk=pk)
        obj = step.content_object
        redirect_url = _redirect_target(request, obj)

        if step.statut != EtapeStatut.EN_ATTENTE:
            messages.error(request, "Cette étape a déjà été traitée.")
            return redirect(redirect_url)
        if step.is_bloquee:
            messages.error(request, "L'étape précédente doit être validée en premier.")
            return redirect(redirect_url)
        if not (request.user.is_admin_role() or request.user.role == step.role_requis):
            messages.error(request, "Vous n'êtes pas autorisé à traiter cette étape.")
            return redirect(redirect_url)

        action = request.POST.get("action")
        commentaire = request.POST.get("commentaire", "").strip()
        signature_nom = (
            request.POST.get("signature_nom", "").strip()
            or request.user.get_full_name()
            or request.user.username
        )

        if action == "approuver":
            step.statut = EtapeStatut.APPROUVEE
        elif action == "refuser":
            if not commentaire:
                messages.error(request, "Un commentaire est requis pour refuser une étape.")
                return redirect(redirect_url)
            step.statut = EtapeStatut.REFUSEE
        else:
            messages.error(request, "Action inconnue.")
            return redirect(redirect_url)

        step.commentaire = commentaire
        step.signature_nom = signature_nom
        step.validateur = request.user
        step.date_validation = timezone.now()
        step.save()

        if obj is not None and hasattr(obj, "valide"):
            if step.statut == EtapeStatut.REFUSEE:
                obj.valide = False
                obj.save(update_fields=["valide"])
            else:
                remaining = ValidationStep.objects.filter(
                    content_type=step.content_type, object_id=step.object_id
                ).exclude(statut=EtapeStatut.APPROUVEE)
                if not remaining.exists():
                    obj.valide = True
                    obj.valide_par = request.user
                    obj.valide_le = timezone.now()
                    obj.save(update_fields=["valide", "valide_par", "valide_le"])

        if step.statut == EtapeStatut.APPROUVEE:
            messages.success(request, f"Étape « {step.libelle} » approuvée et signée.")
        else:
            messages.warning(request, f"Étape « {step.libelle} » refusée. Le circuit est bloqué.")

        return redirect(redirect_url)
