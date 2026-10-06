from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from decouple import config

from accounts.models import Role, User


class Command(BaseCommand):
    help = (
        "Crée le compte administrateur à partir de ADMIN_USERNAME / ADMIN_PASSWORD "
        "s'il n'existe encore aucun administrateur. Sans effet ensuite."
    )

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("Un administrateur existe déjà.")
            return

        password = config("ADMIN_PASSWORD", default="")
        if not password:
            raise CommandError("Aucun administrateur : définissez ADMIN_PASSWORD pour en créer un.")
        if len(password) < 10:
            raise CommandError("ADMIN_PASSWORD doit contenir au moins 10 caractères.")

        username = config("ADMIN_USERNAME", default="admin")
        user = User.objects.filter(username=username).first() or User(username=username)
        user.role = Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.email = config("ADMIN_EMAIL", default=user.email or "")
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Administrateur « {username} » créé ({settings.SITE_URL})."))
