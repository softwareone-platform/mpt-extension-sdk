"""
Django settings for pippo project.

Generated by 'django-admin startproject' using Django 4.2.8.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
from pathlib import Path

from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "MPT_DJANGO_SECRET_KEY",
    "",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "mpt_extension_sdk.runtime.djapp.apps.DjAppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "mpt_extension_sdk.runtime.djapp.middleware.MPTClientMiddleware",
]

ROOT_URLCONF = "mpt_extension_sdk.runtime.djapp.conf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# OpenTelemetry configuration
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv(
    "APPLICATIONINSIGHTS_CONNECTION_STRING", ""
)
USE_APPLICATIONINSIGHTS = APPLICATIONINSIGHTS_CONNECTION_STRING != ""


if USE_APPLICATIONINSIGHTS:  # pragma: no cover
    logger_provider = LoggerProvider()
    set_logger_provider(logger_provider)
    exporter = AzureMonitorLogExporter(
        connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {name} {levelname} (pid: {process}, thread: {thread}) {message}",
            "style": "{",
        },
        "rich": {
            "format": "{message}",
            "style": "{",
        },
        "opentelemetry": {
            "format": "(pid: {process}, thread: {thread}) {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "rich": {
            "class": "mpt_extension_sdk.runtime.logging.RichHandler",
            "formatter": "rich",
            "log_time_format": lambda x: x.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "rich_tracebacks": True,
        },
        "opentelemetry": {
            "class": "opentelemetry.sdk._logs.LoggingHandler",
            "formatter": "opentelemetry",
        },
    },
    "root": {
        "handlers": ["rich"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["rich"],
            "level": "INFO",
            "propagate": False,
        },
        "swo.mpt": {
            "handlers": ["rich"],
            "level": "DEBUG",
            "propagate": False,
        },
        "azure": {
            "handlers": ["rich"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Proxy settings
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# MPT settings

MPT_API_BASE_URL = os.getenv("MPT_API_BASE_URL", "http://localhost:8000")
MPT_API_TOKEN = os.getenv("MPT_API_TOKEN", "change-me!")
MPT_API_TOKEN_OPERATIONS = os.getenv("MPT_API_TOKEN_OPERATIONS", "change-me!")
MPT_PRODUCTS_IDS = os.getenv("MPT_PRODUCTS_IDS", "PRD-1111-1111")
MPT_PORTAL_BASE_URL = os.getenv("MPT_PORTAL_BASE_URL", "https://portal.s1.show")
MPT_KEY_VAULT_NAME = os.getenv("MPT_KEY_VAULT_NAME", "mpt-key-vault")

MPT_ORDERS_API_POLLING_INTERVAL_SECS = int(
    os.getenv("MPT_ORDERS_API_POLLING_INTERVAL_SECS", "120")
)

EXTENSION_CONFIG = {
    "DUE_DATE_DAYS": "30",
    "ORDER_CREATION_WINDOW_HOURS": os.getenv("EXT_ORDER_CREATION_WINDOW_HOURS", "24"),
}

MPT_SETUP_CONTEXTS_FUNC = os.getenv(
    "MPT_SETUP_CONTEXTS_FUNC",
    "mpt_extension_sdk.runtime.events.utils.setup_contexts",
)
