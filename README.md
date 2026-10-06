# Ayden Transit

Plateforme de gestion centralisée pour les transitaires, commissionnaires en douane, entreprises import-export et acteurs de la logistique. Ayden Transit remplace le suivi éparpillé entre WhatsApp, Excel, papier et appels téléphoniques par un espace unique, accessible depuis un ordinateur ou un téléphone.

## Modules couverts (v1)

- **Comptes & rôles** : administrateur, direction, agent de transit, comptable, consultation.
- **Clients & tiers** : clients, fournisseurs, transporteurs, prestataires, agents en douane, banques/assurances.
- **Dossiers de transit** : numérotation automatique (`AT-2026-0001`), référence client, donneur d'ordre, type d'opération (import/export/transit/douane), régime douanier, Incoterm, origine/provenance/destination, agent responsable, statut, validation interne.
- **Marchandises / cargo** : désignation, code SH/HS indicatif, quantité, colisage, poids, valeur déclarée, origine.
- **Documents** : facture commerciale, connaissement (B/L), LTA, CMR, liste de colisage, certificat d'origine, DAU, assurance, autorisations — téléversés et rattachés à chaque dossier.
- **Devis, proformas & factures** : lignes détaillées par type de frais (honoraires de transit, débours, droits et taxes, acconage, manutention, transport), note de détail par dossier.
- **TVA** : taux par ligne (0, 7, 10, 14, 20 %) proposé selon le type de frais (honoraires, acconage, manutention : 20 % ; transport : 14 % ; débours, droits et taxes : 0 %), totaux HT / TVA / TTC et ventilation par taux ; le solde dû est calculé sur le TTC. Un client peut être marqué *exonéré de TVA* (zone franche, export...) avec le motif à imprimer : ses devis et factures sont établis à 0 % et portent la mention d'exonération. L'exonération est figée sur chaque document à sa création, pour qu'un changement ultérieur sur la fiche client ne modifie pas les factures déjà émises.
- **Portail client** (`/portail/`) : vos clients se connectent avec un compte au rôle *Client (portail)* rattaché à leur société, créé depuis la fiche client (*Créer un accès*). Ils suivent leurs dossiers (statut, étapes de suivi, marchandises), téléchargent leurs documents et leurs devis/factures en PDF, et voient leur solde à régler. Ils ne voient jamais les autres clients, les brouillons, ni les événements marqués internes (les notes internes ne sont jamais visibles ; les incidents sont internes par défaut). Les comptes clients sont cantonnés au portail par un middleware.
- **Alertes** : centre d'alertes (cloche dans la barre de navigation + bloc « À traiter en priorité » au tableau de bord) recalculé en continu : factures échues impayées (critiques au-delà de 30 jours), incidents ouverts sur les dossiers, dossiers sans activité depuis 7 jours, devis envoyés expirés ou sur le point d'expirer, factures fournisseurs à payer (comptabilité/direction), validations en attente pour son rôle. Filtres par catégorie et « mes dossiers ». Seuils réglables dans `.env` (`ALERTE_*`).
- **Impression PDF** : devis, proformas et factures en PDF (A4) avec en-tête de la société, logo, mentions légales (ICE, RC, IF...), RIB, récapitulatif par type de frais, montant en toutes lettres et, pour les factures, règlements reçus et reste à payer. Les informations de la société se règlent dans *Société (en-tête PDF)* (administrateurs).
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
alerts/       Alertes calculées (échéances, incidents, inactivité, validations)
portal/       Portail client (lecture seule, limité à la société du client)
dashboard/    Tableau de bord et indicateurs
core/         Éléments partagés (numérotation, templates de base, filtres)
```

## Déploiement en production

- Définir `DEBUG=False`, un `SECRET_KEY` fort et `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`.
- Basculer `DB_ENGINE=postgres` et renseigner les variables `DB_*`.
- Exécuter `python manage.py collectstatic`.
- Servir l'application avec Gunicorn derrière un reverse proxy (Nginx, etc.).
- **Fichiers téléversés** : ne pas exposer `MEDIA_ROOT` publiquement sur le reverse proxy (les chemins des documents sont prévisibles). Le portail client télécharge les documents via une vue contrôlée ; idéalement, faire de même côté interne ou restreindre `/media/` aux utilisateurs connectés.
