"""
Django settings for Ayden Transit.
"""

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-change-me-in-production-1hg%t*7zemwk1@7qkdfjlx",
)

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default="", cast=Csv()
)

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
            "NAME": BASE_DIR / "db.sqlite3",
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
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Currency used across quotes/invoices when not overridden per record
DEFAULT_CURRENCY = config("DEFAULT_CURRENCY", default="MAD")

# Alertes
ALERTE_DOSSIER_INACTIF_JOURS = config("ALERTE_DOSSIER_INACTIF_JOURS", default=7, cast=int)
ALERTE_FACTURE_RETARD_CRITIQUE_JOURS = config("ALERTE_FACTURE_RETARD_CRITIQUE_JOURS", default=30, cast=int)
ALERTE_ECHEANCE_PROCHE_JOURS = config("ALERTE_ECHEANCE_PROCHE_JOURS", default=3, cast=int)

# Fichiers téléversés : jamais publiés tels quels. En production derrière Nginx, renseigner
# le préfixe d'une location `internal` pointant sur MEDIA_ROOT (voir README) pour que Nginx
# envoie les fichiers après le contrôle d'accès de Django.
PROTECTED_MEDIA_ACCEL_PREFIX = config("PROTECTED_MEDIA_ACCEL_PREFIX", default="")
