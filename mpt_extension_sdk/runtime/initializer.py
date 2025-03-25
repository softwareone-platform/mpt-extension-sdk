import os

import rich
from rich.theme import Theme

from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
    DJANGO_SETTINGS_MODULE,
)
from mpt_extension_sdk.runtime.djapp.conf import extract_product_ids
from mpt_extension_sdk.runtime.events.utils import instrument_logging
from mpt_extension_sdk.runtime.utils import (
    get_extension_app_config_name,
    get_extension_variables,
)

# TODO: Move this out of sdk
JSON_EXT_VARIABLES = {
    "EXT_WEBHOOKS_SECRETS",
    "EXT_AIRTABLE_BASES",
    "EXT_AIRTABLE_PRICING_BASES",
    "EXT_PRODUCT_SEGMENT",
}


def initialize(options):
    rich.reconfigure(theme=Theme({"repr.mpt_id": "bold light_salmon3"}))
    group = options.get("app_config_group", DEFAULT_APP_CONFIG_GROUP)
    name = options.get("app_config_name", DEFAULT_APP_CONFIG_NAME)
    django_settings_module = options.get("django_settings_module", DJANGO_SETTINGS_MODULE)
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", django_settings_module
    )
    import django
    from django.conf import settings

    root_logging_handler = "rich" if options.get("color") else "console"
    if settings.USE_APPLICATIONINSIGHTS:
        logging_handlers = [root_logging_handler, "opentelemetry"]
    else:
        logging_handlers = [root_logging_handler]

    logging_level = "DEBUG" if options.get("debug") else "INFO"

    app_config_name = get_extension_app_config_name(group=group, name=name)
    app_root_module, _ = app_config_name.split(".", 1)
    settings.DEBUG = options.get("debug", False)
    settings.INSTALLED_APPS.append(app_config_name)
    settings.LOGGING["root"]["handlers"] = logging_handlers
    settings.LOGGING["loggers"]["swo.mpt"]["handlers"] = logging_handlers
    settings.LOGGING["loggers"]["swo.mpt"]["level"] = logging_level
    settings.LOGGING["loggers"][app_root_module] = {
        "handlers": logging_handlers,
        "level": logging_level,
        "propagate": False,
    }
    settings.EXTENSION_CONFIG.update(get_extension_variables(JSON_EXT_VARIABLES))
    settings.MPT_PRODUCTS_IDS = extract_product_ids(settings.MPT_PRODUCTS_IDS)

    if settings.USE_APPLICATIONINSIGHTS:
        instrument_logging()

    django.setup()
