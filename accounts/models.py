from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Administrateur"
    DIRECTION = "direction", "Direction"
    AGENT_TRANSIT = "agent_transit", "Agent de transit"
    COMPTABLE = "comptable", "Comptable"
    CONSULTATION = "consultation", "Consultation seule"
    CLIENT = "client", "Client (portail)"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT_TRANSIT)
    phone = models.CharField("Téléphone", max_length=30, blank=True)
    service = models.CharField("Service / département", max_length=100, blank=True)
    partner = models.ForeignKey(
        "partners.Partner", verbose_name="Société cliente (portail)",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="comptes_portail",
        help_text="Uniquement pour le rôle « Client (portail) » : le client ne voit que ses propres dossiers.",
    )

    recap_alertes_email = models.BooleanField(
        "Recevoir le récapitulatif des alertes par e-mail", default=True,
        help_text="Envoyé chaque matin s'il y a des alertes qui vous concernent (équipe uniquement).",
    )

    @property
    def is_client_portal(self):
        return self.role == Role.CLIENT

    def is_admin_role(self):
        return self.role == Role.ADMIN or self.is_superuser

    def can_validate(self):
        return self.role in (Role.ADMIN, Role.DIRECTION) or self.is_superuser

    def can_manage_billing(self):
        return self.role in (Role.ADMIN, Role.COMPTABLE, Role.DIRECTION) or self.is_superuser

    def __str__(self):
        full = self.get_full_name()
        return full if full else self.username
