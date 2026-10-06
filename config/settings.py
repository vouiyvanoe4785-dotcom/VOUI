"""
Django settings for Ayden Transit.
"""

from pathlib import Path
from decouple import config, Csv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

_INSECURE_SECRET_KEY_PREFIX = "django-insecure-"

SECRET_KEY = config(
    "SECRET_KEY",
    default=_INSECURE_SECRET_KEY_PREFIX + "change-me-in-production-1hg%t*7zemwk1@7qkdfjlx",
)

# Secure by default: DEBUG must be explicitly enabled (e.g. via .env for local dev).
DEBUG = config("DEBUG", default=False, cast=bool)

if not DEBUG and SECRET_KEY.startswith(_INSECURE_SECRET_KEY_PREFIX):
    raise ImproperlyConfigured(
        "Refusing to start with DEBUG=False and the default SECRET_KEY. "
        "Set a real SECRET_KEY via the environment before deploying."
    )

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default="", cast=Csv()
)

# Set automatically by Render to the service's public hostname (xxx.onrender.com).
RENDER_EXTERNAL_HOSTNAME = config("RENDER_EXTERNAL_HOSTNAME", default="")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# Where the SQLite database and uploaded files live; point it at a persistent disk in production.
DATA_DIR = Path(config("DATA_DIR", default=str(BASE_DIR)))

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "widget_tweaks",
    # Ayden Transit apps
    "core",
    "accounts",
    "partners",
    "dossiers",
    "cargo",
    "documents",
    "billing",
    "purchasing",
    "treasury",
    "approvals",
    "reports",
    "tracking",
    "alerts",
    "portal",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.PortalAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "alerts.context_processors.alertes",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# Defaults to SQLite for easy local development; set DB_ENGINE=postgres for production.

if config("DB_ENGINE", default="sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="ayden_transit"),
            "USER": config("DB_USER", default="ayden_transit"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATA_DIR / "db.sqlite3",
            # WAL + immediate transactions avoid "database is locked" with several gunicorn workers.
            "OPTIONS": {
                "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
                "transaction_mode": "IMMEDIATE",
            },
        }
    }


AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.ERROR: "danger",
}

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

# Internationalization

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = config("TIME_ZONE", default="Africa/Casablanca")
USE_I18N = True
USE_TZ = True


# Static files

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        # Le manifeste (noms hachés) n'existe qu'après collectstatic : on ne l'exige
        # qu'en production, pour que le serveur de dev et les tests fonctionnent sans.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# Media files (uploaded documents)

MEDIA_URL = "media/"
MEDIA_ROOT = DATA_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Currency used across quotes/invoices when not overridden per record
DEFAULT_CURRENCY = config("DEFAULT_CURRENCY", default="MAD")

# Alertes
ALERTE_DOSSIER_INACTIF_JOURS = config("ALERTE_DOSSIER_INACTIF_JOURS", default=7, cast=int)
ALERTE_FACTURE_RETARD_CRITIQUE_JOURS = config("ALERTE_FACTURE_RETARD_CRITIQUE_JOURS", default=30, cast=int)
ALERTE_ECHEANCE_PROCHE_JOURS = config("ALERTE_ECHEANCE_PROCHE_JOURS", default=3, cast=int)
ALERTE_REPONSE_DEVIS_JOURS = config("ALERTE_REPONSE_DEVIS_JOURS", default=7, cast=int)

# Adresse publique de l'application, pour les liens des e-mails envoyés hors requête
# (récapitulatif quotidien des alertes).
SITE_URL = config(
    "SITE_URL",
    default=f"https://{RENDER_EXTERNAL_HOSTNAME}" if RENDER_EXTERNAL_HOSTNAME else "http://127.0.0.1:8000",
).rstrip("/")

# Fichiers téléversés : jamais publiés tels quels. En production derrière Nginx, renseigner
# le préfixe d'une location `internal` pointant sur MEDIA_ROOT (voir README) pour que Nginx
# envoie les fichiers après le contrôle d'accès de Django.
PROTECTED_MEDIA_ACCEL_PREFIX = config("PROTECTED_MEDIA_ACCEL_PREFIX", default="")

# E-mail (réinitialisation des mots de passe, etc.). En développement, les e-mails
# sont affichés dans la console ; en production, renseigner le serveur SMTP.
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend" if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Ayden Transit <no-reply@localhost>")

# Lien de réinitialisation du mot de passe valable 24 h.
PASSWORD_RESET_TIMEOUT = config("PASSWORD_RESET_TIMEOUT", default=60 * 60 * 24, cast=int)

# Derrière un reverse proxy HTTPS (Nginx), pour que Django sache que la requête est
# sécurisée et génère des liens https:// dans les e-mails.
BEHIND_HTTPS_PROXY = config("BEHIND_HTTPS_PROXY", default=False, cast=bool)
if BEHIND_HTTPS_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HTTPS en production : cookies de session et CSRF uniquement en HTTPS (désactivable
# avec HTTPS_ONLY=False pour un serveur interne en HTTP), redirection HTTP -> HTTPS si
# elle n'est pas déjà faite par Nginx, et HSTS sur option (difficile à annuler : ne
# l'activer qu'une fois le HTTPS en place durablement).
HTTPS_ONLY = config("HTTPS_ONLY", default=not DEBUG, cast=bool)
SESSION_COOKIE_SECURE = HTTPS_ONLY
CSRF_COOKIE_SECURE = HTTPS_ONLY
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool)

# Errors (tracebacks of 500s) go to stderr, so they show up in the host's logs.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
