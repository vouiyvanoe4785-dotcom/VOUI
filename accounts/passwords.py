from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.models import Societe

EMAIL_TEMPLATE = "accounts/emails/password_reset.txt"
SUBJECT_TEMPLATE = "accounts/emails/password_reset_subject.txt"


def extra_email_context():
    return {
        "site_name": Societe.load().raison_sociale,
        "validite_heures": settings.PASSWORD_RESET_TIMEOUT // 3600,
    }


def email_context(request, user):
    """Same context Django's PasswordResetForm gives the reset e-mail templates."""
    return {
        "email": user.email,
        "domain": request.get_host(),
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "user": user,
        "token": default_token_generator.make_token(user),
        "protocol": "https" if request.is_secure() else "http",
        **extra_email_context(),
    }


def envoyer_lien_reinitialisation(request, user):
    """Send a reset link to one specific user (used by admins from the team list)."""
    ctx = email_context(request, user)
    subject = "".join(render_to_string(SUBJECT_TEMPLATE, ctx).splitlines())
    send_mail(subject, render_to_string(EMAIL_TEMPLATE, ctx), None, [user.email])
