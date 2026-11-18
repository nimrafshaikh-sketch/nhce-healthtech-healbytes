import os

from .base import *  # noqa

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

# Trust TLS termination headers when deployed behind the Nginx reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "healbytes"),
        "USER": os.environ.get("POSTGRES_USER", "healbytes"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}
