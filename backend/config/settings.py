"""Configuración de Django para SIRAC. Todo lo sensible viene de variables de entorno (.env en el servidor)."""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "solo-para-desarrollo-local-no-usar-en-produccion")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend,testserver").split(",")
CSRF_TRUSTED_ORIGINS = ["https://sirac.dbltech.tech"]

INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "django.contrib.staticfiles", "ia", "crm"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []

DATABASES = {"default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=60)}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT.mkdir(exist_ok=True)

# Detrás de Caddy (HTTPS): confiar en la cabecera del proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
VERSION = os.environ.get("GIT_SHA", "local")

# CRM: contraseña de las cuentas de demostración (solo en el .env del servidor; si falta, se genera una al azar)
CRM_CLAVE_DEMO = os.environ.get("CRM_CLAVE_DEMO", "")
# WhatsApp real con Evolution API (contenedor interno). Sin EVOLUTION_URL/API_KEY la integración queda apagada.
EVOLUTION_URL = os.environ.get("EVOLUTION_URL", "")
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCIA = os.environ.get("EVOLUTION_INSTANCIA", "sirac")
EVOLUTION_WEBHOOK_TOKEN = os.environ.get("EVOLUTION_WEBHOOK_TOKEN", "")
EVOLUTION_WEBHOOK_BASE = os.environ.get("EVOLUTION_WEBHOOK_BASE", "http://backend:8000")
SITIO_URL = os.environ.get("SITIO_URL", "https://sirac.dbltech.tech")
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
