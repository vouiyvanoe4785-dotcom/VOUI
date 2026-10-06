# Ayden Transit

Plateforme de gestion centralisée pour les transitaires, commissionnaires en douane, entreprises import-export et acteurs de la logistique. Ayden Transit remplace le suivi éparpillé entre WhatsApp, Excel, papier et appels téléphoniques par un espace unique, accessible depuis un ordinateur ou un téléphone.

## Modules couverts

- **Comptes & rôles** : administrateur, direction, agent de transit, comptable, consultation, client (portail). *Mot de passe oublié* par e-mail (lien à usage unique valable 24 h), *Changer mon mot de passe* dans le menu, et envoi d'un lien de réinitialisation par l'administrateur depuis la liste de l'équipe.
- **Clients & tiers** : clients, fournisseurs, transporteurs, prestataires, agents en douane, banques/assurances.
- **Dossiers de transit** : numérotation automatique (`AT-2026-0001`), référence client, donneur d'ordre, type d'opération (import/export/transit/douane), régime douanier, Incoterm, origine/provenance/destination, agent responsable, statut.
- **Marchandises / cargo** : désignation, code SH/HS indicatif, quantité, colisage, poids, valeur déclarée, origine.
- **Documents** : facture commerciale, connaissement (B/L), LTA, CMR, liste de colisage, certificat d'origine, DAU, assurance, autorisations — téléversés et rattachés à chaque dossier (extensions restreintes aux formats documentaires usuels).
- **Devis, proformas & factures** : lignes détaillées par type de frais (honoraires de transit, débours, droits et taxes, acconage, manutention, transport), note de détail par dossier.
- **TVA** : taux par ligne (0, 7, 10, 14, 20 %) proposé selon le type de frais (honoraires, acconage, manutention : 20 % ; transport : 14 % ; débours, droits et taxes : 0 %), totaux HT / TVA / TTC et ventilation par taux ; le solde dû est calculé sur le TTC. Un client peut être marqué *exonéré de TVA* (zone franche, export...) avec le motif à imprimer : ses devis et factures sont établis à 0 % et portent la mention d'exonération. L'exonération est figée sur chaque document à sa création, pour qu'un changement ultérieur sur la fiche client ne modifie pas les factures déjà émises.
- **Achats & factures fournisseurs** : factures reçues des fournisseurs/prestataires/transporteurs, rattachées à un dossier, avec la même gestion de TVA (taux proposés : 20 % y compris sur les débours facturés par un prestataire, 14 % transport, 0 % droits et taxes de douane) et paiements.
- **Caisse & trésorerie** : plusieurs caisses/comptes, mouvements manuels, virements internes, et encaissements/décaissements auto-liés aux paiements clients et fournisseurs.
- **Paiements & recouvrement** : enregistrement des paiements (espèces, chèque, virement, effet), suivi du solde, historique des relances clients.
- **Validations & signature électronique** : circuit de validation multi-niveaux (par rôle requis, dans l'ordre) avec signature nominative, horodatage et commentaire — configuré pour les dossiers et les factures.
- **Rapports par service** : chiffre d'affaires facturé/encaissé et dépenses engagées/payées par service et par période, synthèse TVA (CA HT, TVA collectée, TVA déductible, TVA nette), avec export CSV.
- **Impression PDF** : devis, proformas et factures en PDF (A4) avec en-tête de la société, logo, mentions légales (ICE, RC, IF...), RIB, récapitulatif par type de frais, montant en toutes lettres et, pour les factures, règlements reçus et reste à payer. Les informations de la société se règlent dans *Société (en-tête PDF)* (administrateurs).
- **Suivi des dossiers** : journal chronologique de chaque dossier (ETA, arrivée, déclaration, visite, liquidation, BAE, enlèvement, livraison, incidents, notes internes), historique automatique des changements de statut, fil d'activité global filtrable.
- **Alertes** : centre d'alertes (cloche dans la barre de navigation + bloc « À traiter en priorité » au tableau de bord) recalculé en continu : factures échues impayées (critiques au-delà de 30 jours), incidents ouverts sur les dossiers, dossiers sans activité depuis 7 jours, devis envoyés expirés ou sur le point d'expirer, factures fournisseurs à payer (comptabilité/direction), validations en attente pour son rôle. Filtres par catégorie et « mes dossiers ». Seuils réglables dans `.env` (`ALERTE_*`). **Récapitulatif quotidien par e-mail** (`python manage.py envoyer_alertes`, à planifier) : la direction et l'administration reçoivent tout, la comptabilité les sujets financiers, les agents leurs dossiers et leurs validations ; rien n'est envoyé s'il n'y a rien à signaler, et le récapitulatif se désactive par utilisateur.
- **Portail client** (`/portail/`) : vos clients se connectent avec un compte au rôle *Client (portail)* rattaché à leur société, créé depuis la fiche client (*Créer un accès*). Ils suivent leurs dossiers (statut, étapes de suivi, marchandises), téléchargent leurs documents et leurs devis/factures en PDF, et voient leur solde à régler. Ils peuvent **accepter ou refuser un devis en ligne** (nom signé + case d'accord, motif facultatif) tant qu'il est envoyé et valable : le statut se met à jour, la réponse apparaît dans le suivi du dossier, sur la fiche et le PDF du devis (« Bon pour accord »), l'auteur du devis et l'agent du dossier reçoivent un e-mail, et une alerte « Réponses clients aux devis » s'affiche pendant 7 jours. Ils ne voient jamais les autres clients, les brouillons, ni les événements marqués internes (les notes internes ne sont jamais visibles ; les incidents sont internes par défaut). Les comptes clients sont cantonnés au portail par un middleware.
- **Tableau de bord** : dossiers par statut / type d'opération, dossiers récents, factures impayées, activité récente, trésorerie, dettes fournisseurs, indicateurs clés.

## Stack technique

- Python 3.11 / Django 5
- Base de données : SQLite en développement, PostgreSQL recommandé en production
- Frontend : templates Django + Bootstrap 5 (responsive, utilisable sur mobile)
- Fichiers statiques servis via WhiteNoise

## Lancer l'application (le plus simple)

1. Installer Python 3.11 ou plus récent depuis https://www.python.org/downloads/ (sous Windows, cocher **« Add Python to PATH »** pendant l'installation).
2. Télécharger le projet depuis GitHub (bouton vert **Code → Download ZIP**, en choisissant la branche `claude/transit-logistics-app-2gy3ka`) et le décompresser.
3. Double-cliquer sur **`lancer.bat`** (Windows) ou lancer **`./lancer.sh`** (Mac / Linux).

Le premier lancement installe tout (quelques minutes), crée la base de données et des **données de démonstration**, puis ouvre le navigateur sur `http://127.0.0.1:8000`. Les lancements suivants sont immédiats et conservent vos données.

Comptes de démonstration (mot de passe **`ayden2026`** pour tous) :

| Identifiant | Rôle |
|---|---|
| `admin` | Administrateur (accès complet) |
| `direction` | Direction |
| `compta` | Comptable |
| `agent`, `agent2` | Agents de transit (services Import / Export) |
| `client` | Client sur le portail (Atlas Industries) |

Pensez à changer ces mots de passe (menu utilisateur → *Changer mon mot de passe*) avant d'y saisir de vraies données. Pour repartir de zéro : arrêter l'application et supprimer le fichier `db.sqlite3`.

L'application tourne sur votre ordinateur : les autres postes du bureau n'y ont pas accès tant qu'elle n'est pas installée sur un serveur (voir *Déploiement en production*).

## Démarrage manuel (développeurs)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # contient DEBUG=True pour le développement ; ajustez SECRET_KEY, etc.

python manage.py migrate
python manage.py demo            # ou : python manage.py createsuperuser
python manage.py runserver
```

L'application est ensuite accessible sur `http://127.0.0.1:8000/`.

## Tests

La suite de tests automatisés (Django `TestCase`) couvre les permissions par rôle, les calculs financiers (totaux, TVA, soldes), la numérotation automatique, le circuit de validation multi-niveaux, les mouvements de caisse, le rapport par service, le portail client, les alertes et la réinitialisation de mot de passe.

Lancer les tests avec le `.env` de développement (ou `DEBUG=True` dans l'environnement : sans lui, l'application refuse de démarrer avec la clé secrète par défaut, et le lanceur de tests force `DEBUG=False`, ce qui exige aussi d'avoir généré les fichiers statiques) :

```bash
python manage.py collectstatic --no-input
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
tracking/     Suivi chronologique des dossiers
alerts/       Alertes calculées (échéances, incidents, inactivité, validations)
portal/       Portail client (lecture seule, limité à la société du client)
dashboard/    Tableau de bord et indicateurs
core/         Éléments partagés (numérotation, templates de base, filtres)
```

## Déploiement en production

- Définir `DEBUG=False`, un `SECRET_KEY` fort et `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`. Avec `DEBUG=False`, l'application refuse de démarrer si la clé par défaut du dépôt est encore utilisée. Générer une clé : `python -c "import secrets; print(secrets.token_urlsafe(50))"`.
- **HTTPS** : avec `DEBUG=False`, les cookies de session et CSRF ne circulent qu'en HTTPS (`HTTPS_ONLY=False` pour un serveur interne en HTTP). Faire la redirection HTTP → HTTPS dans Nginx ou mettre `SECURE_SSL_REDIRECT=True`. Une fois le HTTPS en place durablement, activer HSTS avec `SECURE_HSTS_SECONDS=31536000`. `python manage.py check --deploy` liste ce qui reste à régler.
- Basculer `DB_ENGINE=postgres` et renseigner les variables `DB_*`.
- Exécuter `python manage.py collectstatic`.
- **Récapitulatif des alertes** : définir `SITE_URL` (adresse publique, pour les liens) puis planifier la commande, par exemple du lundi au samedi à 7 h 30 :

  ```cron
  30 7 * * 1-6  cd /chemin/vers/ayden && .venv/bin/python manage.py envoyer_alertes
  ```

  `--dry-run` montre qui recevrait quoi sans rien envoyer ; `--utilisateur <identifiant>` envoie à une seule personne (test).
- **E-mail** : renseigner `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` (sinon aucun e-mail de réinitialisation ne part). Derrière Nginx en HTTPS, mettre `BEHIND_HTTPS_PROXY=True` et transmettre `X-Forwarded-Proto` pour que les liens envoyés soient en `https://`.
- Servir l'application avec Gunicorn derrière un reverse proxy (Nginx, etc.).
- **Fichiers téléversés** : l'application ne publie jamais `MEDIA_ROOT` ; chaque document passe par une vue qui vérifie l'accès (connexion côté interne, propriété du dossier côté portail). Ne créez **pas** de `location /media/` publique. Pour que Nginx envoie lui-même les fichiers après ce contrôle, définissez `PROTECTED_MEDIA_ACCEL_PREFIX=/protected-media/` et ajoutez :

  ```nginx
  location /protected-media/ {
      internal;                      # inaccessible directement depuis l'extérieur
      alias /chemin/vers/ayden/media/;
  }
  ```
