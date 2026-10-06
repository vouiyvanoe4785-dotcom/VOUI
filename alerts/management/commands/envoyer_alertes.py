from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from alerts.recap import destinataires, envoyer_recap


class Command(BaseCommand):
    help = (
        "Envoie à chaque membre de l'équipe le récapitulatif de ses alertes par e-mail. "
        "À planifier chaque matin (cron), par exemple : 30 7 * * 1-6 python manage.py envoyer_alertes"
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Affiche qui recevrait quoi, sans envoyer.")
        parser.add_argument("--utilisateur", help="N'envoyer qu'à cet identifiant (test).")

    def handle(self, *args, dry_run=False, utilisateur=None, **options):
        users = destinataires()
        if utilisateur:
            users = users.filter(username=utilisateur)
            if not users.exists():
                if User.objects.filter(username=utilisateur).exists():
                    raise CommandError(
                        f"{utilisateur} ne reçoit pas le récapitulatif (pas d'e-mail, compte inactif, "
                        "client/consultation, ou récapitulatif désactivé)."
                    )
                raise CommandError(f"Utilisateur inconnu : {utilisateur}")

        envoyes = envoyer_recap(users, dry_run=dry_run)
        verbe = "recevrait" if dry_run else "a reçu"
        for user, nombre in envoyes:
            self.stdout.write(f"{user.username} <{user.email}> {verbe} {nombre} alerte(s)")
        self.stdout.write(self.style.SUCCESS(
            f"{len(envoyes)} e-mail(s) {'à envoyer' if dry_run else 'envoyé(s)'}."
        ))
