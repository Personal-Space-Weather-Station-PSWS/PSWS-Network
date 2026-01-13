# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------

from pathlib import Path
import os

from dotenv import load_dotenv

# ---------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------

# base.py -> src/psws/settings/base.py
# parents[3] = repo root
BASE_DIR = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------
# Load environment (.env)
# ---------------------------------------------------------------------

# Allow override via environment (Apache SetEnv)
ENV_FILE = os.environ.get("PSWS_ENV_FILE", BASE_DIR / "deploy/env/psws.env")

load_dotenv(dotenv_path=ENV_FILE, override=False)

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

def env_required(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

def env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")

def env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except ValueError:
        return default

def env_list(key: str, default: str = "") -> list[str]:
    return [x.strip() for x in os.environ.get(key, default).split(",") if x.strip()]

# ---------------------------------------------------------------------
# Core Django
# ---------------------------------------------------------------------

SECRET_KEY = env_required("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

DEFAULT_AUTO_FIELD = env(
    "DJANGO_DEFAULT_AUTO_FIELD",
    "django.db.models.BigAutoField"
)

ROOT_URLCONF = env("DJANGO_ROOT_URLCONF", "psws.urls")
WSGI_APPLICATION = env("DJANGO_WSGI_APPLICATION", "psws.wsgi.application")

LOGIN_REDIRECT_URL = env("DJANGO_LOGIN_REDIRECT_URL", "/home")
LOGIN_URL = env("DJANGO_LOGIN_URL", "/accounts/login/")

# ---------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "bootstrap4",
    "crispy_forms",
    "crispy_bootstrap4",
    "django_tables2",
    "django_filters",
    "six",
    'django_smoke_tests',
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.api",
    "apps.core",
    "apps.datarequests",
    "apps.stations",
    "apps.observations",
    "apps.datatypes",
    "apps.bands",
    "apps.instruments",
    "apps.instrumenttypes",
    "apps.centerfrequencies",
    "apps.analysis",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------
# External Secrets
# ---------------------------------------------------------------------
MAPBOX_ACCESS_TOKEN= env("MAPBOX_ACCESS_TOKEN", "")
ACCOUNT_ACTIVATION_LOG_PATH = env("ACCOUNT_ACTIVATION_LOG_PATH", "")

# ---------------------------------------------------------------------
# Other Source Code Confgigurations
# ---------------------------------------------------------------------
ONLINE_CUT_OFF_HOURS = env_int("ONLINE_CUT_OFF_HOURS", 24)
POSSIBLY_ONLINE_CUT_OFF_HOURS = env_int("POSSIBLY_ONLINE_CUT_OFF_HOURS", 48)
RETIREMENT_CUT_OFF_HOURS = env_int("RETIREMENT_CUT_OFF_HOURS", 96)

# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------

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
                "psws.context_processors.psws_public_settings",
            ],
        },
    },
]

# ---------------------------------------------------------------------
# Database (MySQL)
# ---------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": env("PSWS_DB_ENGINE", "django.db.backends.mysql"),
        "NAME": env_required("PSWS_DB_NAME"),
        "USER": env_required("PSWS_DB_USER"),
        "PASSWORD": env_required("PSWS_DB_PASSWORD"),
        "HOST": env("PSWS_DB_HOST", "localhost"),
        "PORT": env("PSWS_DB_PORT", "3306"),
        "CONN_MAX_AGE": env_int("PSWS_DB_CONN_MAX_AGE", 3600),
    }
}

# ---------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------

LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE", "en-us")
TIME_ZONE = env("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ---------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------

STATIC_URL = env("DJANGO_STATIC_URL", "/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = env("DJANGO_MEDIA_URL", "/media/")
MEDIA_ROOT = env("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media"))

# ---------------------------------------------------------------------
# Crispy Forms
# ---------------------------------------------------------------------

CRISPY_TEMPLATE_PACK = env("DJANGO_CRISPY_TEMPLATE_PACK", 'bootstrap4')

# ---------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------

EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = env_int("DJANGO_EMAIL_PORT", 25)
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", False)
EMAIL_USE_SSL = env_bool("DJANGO_EMAIL_USE_SSL", False)
EMAIL_HOST_USER = env("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("DJANGO_EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL", "")
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", "")

# ADMINS="Name:email,Name2:email2"
def parse_admins(raw: str) -> tuple:
    if not raw:
        return ()
    admins = []
    for item in raw.split(","):
        if ":" in item:
            name, email = item.split(":", 1)
            admins.append((name.strip(), email.strip()))
    return tuple(admins)

ADMINS = parse_admins(env("DJANGO_ADMINS", ""))

# ---------------------------------------------------------------------
# Security (fully env-controlled)
# ---------------------------------------------------------------------

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", False)

SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)

X_FRAME_OPTIONS = env("DJANGO_X_FRAME_OPTIONS", "DENY")
SECURE_CONTENT_TYPE_NOSNIFF = env_bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", True
)
SECURE_REFERRER_POLICY = env(
    "DJANGO_SECURE_REFERRER_POLICY", "same-origin"
)

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
"""
LOG_LEVEL = env("DJANGO_LOG_LEVEL", "INFO").upper()
LOG_FILE = env("DJANGO_LOG_FILE", str(BASE_DIR / "logs" / "django.log"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": LOG_LEVEL,
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": LOG_FILE,
            "formatter": "standard",
            "level": LOG_LEVEL,
        },
    },
    "loggers": {
        "django": {
            "handlers": env_list("DJANGO_LOG_HANDLERS", "console,file"),
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}
"""
