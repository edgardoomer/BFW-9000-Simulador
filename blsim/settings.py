"""Configuracion del proyecto Buckley-Leverett."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ----------------------------------------------------------------------------
# Carga minima de .env (evita una dependencia externa solo para esto)
# ----------------------------------------------------------------------------
def _load_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


import os  # noqa: E402  (despues de definir el loader, por claridad)

ENV = {**_load_env(BASE_DIR / ".env"), **os.environ}


def env(key, default=None):
    return ENV.get(key, default)


def env_bool(key, default=False):
    raw = ENV.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "si"}


# ----------------------------------------------------------------------------
# Nucleo
# ----------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-clave-solo-para-desarrollo-local")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = (
    ["*"] if DEBUG
    else [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
)
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in env("DJANGO_CSRF_ORIGINS",
                           "http://localhost:8017,http://127.0.0.1:8017").split(",") if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise sirve los archivos estaticos cuando DEBUG = 0 (caso Docker).
    # Si no esta instalado, se omite y Django los sirve en modo desarrollo.
    *(["whitenoise.middleware.WhiteNoiseMiddleware"]
      if __import__("importlib").util.find_spec("whitenoise") else []),
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "blsim.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context.perfil",
                "core.context.assets",
            ],
        },
    },
]

WSGI_APPLICATION = "blsim.wsgi.application"
ASGI_APPLICATION = "blsim.asgi.application"

# La ruta de la base es configurable para que en Docker pueda vivir en un
# volumen montado y sobrevivir a la reconstruccion de la imagen.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(env("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3"))),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

if __import__("importlib").util.find_spec("whitenoise"):
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "blsim-cache",
    }
}

# ----------------------------------------------------------------------------
# Integracion de precios de crudo (oilpriceapi.com)
# ----------------------------------------------------------------------------
OILPRICE_API_KEY = env("OILPRICE_API_KEY", "")
OILPRICE_API_BASE = env("OILPRICE_API_BASE", "https://api.oilpriceapi.com/v1")
OILPRICE_DEFAULT_CODE = env("OILPRICE_DEFAULT_CODE", "BRENT_CRUDE_USD")
# Minutos que se conserva en cache una cotizacion antes de volver a consultar.
OILPRICE_CACHE_MINUTES = int(env("OILPRICE_CACHE_MINUTES", "30"))
# Precio de respaldo si la API no responde (USD/bbl).
OILPRICE_FALLBACK = float(env("OILPRICE_FALLBACK", "82.00"))

# En equipos con inspeccion TLS corporativa, el bundle de certifi falla.
# truststore delega la validacion al almacen de certificados del sistema
# operativo, que si reconoce la CA del proxy. Si no esta instalado, se ignora.
try:  # pragma: no cover - depende del entorno
    import truststore

    truststore.inject_into_ssl()
except Exception:  # pragma: no cover
    pass
