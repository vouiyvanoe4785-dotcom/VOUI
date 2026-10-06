# Ayden Transit

Plateforme de gestion centralisée pour les transitaires, commissionnaires en douane, entreprises import-export et acteurs de la logistique. Ayden Transit remplace le suivi éparpillé entre WhatsApp, Excel, papier et appels téléphoniques par un espace unique, accessible depuis un ordinateur ou un téléphone.

## Modules couverts

- **Comptes & rôles** : administrateur, direction, agent de transit, comptable, consultation.
- **Clients & tiers** : clients, fournisseurs, transporteurs, prestataires, agents en douane, banques/assurances.
- **Dossiers de transit** : numérotation automatique (`AT-2026-0001`), référence client, donneur d'ordre, type d'opération (import/export/transit/douane), régime douanier, Incoterm, origine/provenance/destination, agent responsable, statut.
- **Marchandises / cargo** : désignation, code SH/HS indicatif, quantité, colisage, poids, valeur déclarée, origine.
- **Documents** : facture commerciale, connaissement (B/L), LTA, CMR, liste de colisage, certificat d'origine, DAU, assurance, autorisations — téléversés et rattachés à chaque dossier (extensions restreintes aux formats documentaires usuels).
- **Devis, proformas & factures** : lignes détaillées par type de frais (honoraires de transit, débours, droits et taxes, acconage, manutention, transport), note de détail par dossier.
- **Achats & factures fournisseurs** : factures reçues des fournisseurs/prestataires/transporteurs, rattachées à un dossier, avec paiements.
- **Caisse & trésorerie** : plusieurs caisses/comptes, mouvements manuels, virements internes, et encaissements/décaissements auto-liés aux paiements clients et fournisseurs.
- **Paiements & recouvrement** : enregistrement des paiements (espèces, chèque, virement, effet), suivi du solde, historique des relances clients.
- **Validations & signature électronique** : circuit de validation multi-niveaux (par rôle requis, dans l'ordre) avec signature nominative, horodatage et commentaire — configuré pour les dossiers et les factures.
- **Rapports par service** : chiffre d'affaires facturé/encaissé et dépenses engagées/payées par service et par période, avec export CSV.
- **Tableau de bord** : dossiers par statut / type d'opération, dossiers récents, factures impayées, trésorerie, dettes fournisseurs.

## Stack technique

- Python 3.11 / Django 5
- Base de données : SQLite en développement, PostgreSQL recommandé en production
- Frontend : templates Django + Bootstrap 5 (responsive, utilisable sur mobile)
- Fichiers statiques servis via WhiteNoise

## Démarrage rapide

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # puis ajustez SECRET_KEY, etc.

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

L'application est ensuite accessible sur `http://127.0.0.1:8000/`.

## Tests

La suite de tests automatisés (Django `TestCase`) couvre les permissions par rôle, les calculs financiers (totaux, soldes), la numérotation automatique, le circuit de validation multi-niveaux, les mouvements de caisse et le rapport par service.

```bash
python manage.py collectstatic --no-input   # requis : le lanceur de tests force DEBUG=False
python manage.py test
```

## Structure du projet

```
config/       Réglages Django, URLs racine
accounts/     Utilisateurs, rôles, équipe
partners/     Clients & tiers
dossiers/     Dossiers de transit (le cœur de l'application)
cargo/        Marchandises / cargo liées aux dossiers
documents/    Documents liés aux dossiers (upload de fichiers)
billing/      Devis, proformas, factures, paiements, relances
purchasing/   Achats & factures fournisseurs, paiements fournisseurs
treasury/     Caisses, comptes de trésorerie, mouvements, virements
approvals/    Circuit de validation multi-niveaux & signature électronique
reports/      Rapports par service, export CSV
dashboard/    Tableau de bord et indicateurs
core/         Éléments partagés (numérotation, templates de base, filtres)
```

## Déploiement en production

- Définir `DEBUG=False`, un `SECRET_KEY` fort et `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`.
  Le démarrage refuse volontairement de se lancer avec `DEBUG=False` si `SECRET_KEY` est resté
  à sa valeur par défaut.
- Basculer `DB_ENGINE=postgres` et renseigner les variables `DB_*`.
- Exécuter `python manage.py collectstatic`.
- Servir l'application avec Gunicorn derrière un reverse proxy (Nginx, etc.).
