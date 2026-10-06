# Ayden Transit

Plateforme de gestion centralisée pour les transitaires, commissionnaires en douane, entreprises import-export et acteurs de la logistique. Ayden Transit remplace le suivi éparpillé entre WhatsApp, Excel, papier et appels téléphoniques par un espace unique, accessible depuis un ordinateur ou un téléphone.

## Modules couverts (v1)

- **Comptes & rôles** : administrateur, direction, agent de transit, comptable, consultation.
- **Clients & tiers** : clients, fournisseurs, transporteurs, prestataires, agents en douane, banques/assurances.
- **Dossiers de transit** : numérotation automatique (`AT-2026-0001`), référence client, donneur d'ordre, type d'opération (import/export/transit/douane), régime douanier, Incoterm, origine/provenance/destination, agent responsable, statut, validation interne.
- **Marchandises / cargo** : désignation, code SH/HS indicatif, quantité, colisage, poids, valeur déclarée, origine.
- **Documents** : facture commerciale, connaissement (B/L), LTA, CMR, liste de colisage, certificat d'origine, DAU, assurance, autorisations — téléversés et rattachés à chaque dossier.
- **Devis, proformas & factures** : lignes détaillées par type de frais (honoraires de transit, débours, droits et taxes, acconage, manutention, transport), note de détail par dossier.
- **Paiements & recouvrement** : enregistrement des paiements (espèces, chèque, virement, effet), suivi du solde, historique des relances clients.
- **Tableau de bord** : dossiers par statut / type d'opération, dossiers récents, factures impayées, activité récente, indicateurs clés.
- **Caisse** : comptes de trésorerie, mouvements détaillés, virements entre caisses.
- **Achats fournisseurs** : factures fournisseurs rattachées aux dossiers, paiements, dettes.
- **Validations & signatures** : circuits de validation multi-étapes avec signature électronique.
- **Rapports par service** : chiffre d'affaires, encaissements et dépenses par service, export CSV.
- **Suivi des dossiers** : journal chronologique de chaque dossier (ETA, arrivée, déclaration, visite, liquidation, BAE, enlèvement, livraison, incidents, notes internes), historique automatique des changements de statut, fil d'activité global filtrable.

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

Lancer les tests :

```bash
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
purchasing/   Achats fournisseurs
treasury/     Caisse et trésorerie
approvals/    Circuits de validation et signatures
reports/      Rapports par service
tracking/     Suivi chronologique des dossiers
dashboard/    Tableau de bord et indicateurs
core/         Éléments partagés (numérotation, templates de base, filtres)
```

## Déploiement en production

- Définir `DEBUG=False`, un `SECRET_KEY` fort et `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`.
- Basculer `DB_ENGINE=postgres` et renseigner les variables `DB_*`.
- Exécuter `python manage.py collectstatic`.
- Servir l'application avec Gunicorn derrière un reverse proxy (Nginx, etc.).
