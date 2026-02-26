import uvicorn
from django.core.asgi import get_asgi_application
from django.core.management import call_command

from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
)
from mpt_extension_sdk.runtime.utils import initialize_extension

DEFAULT_BIND = "0.0.0.0:8080"


def start_event_consumer(options):
    """Start the event consumer."""
    initialize_extension(options)
    call_command("consume_events")


def start_uvicorn(
    options,
    group=DEFAULT_APP_CONFIG_GROUP,
    name=DEFAULT_APP_CONFIG_NAME,
):
    """Start the Uvicorn server for the extension."""
    initialize_extension(options, group=group, name=name)

    handler_name = "rich" if options.get("color") else "console"

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} {name} {levelname} (pid: {process}, "
                "thread: {thread}) {message}",
                "style": "{",
            },
            "rich": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "rich": {
                "class": "rich.logging.RichHandler",
                "formatter": "rich",
                "log_time_format": lambda log_time: log_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "rich_tracebacks": True,
            },
        },
        "root": {
            "handlers": [handler_name],
            "level": "INFO",
        },
        "loggers": {
            "uvicorn": {
                "handlers": [handler_name],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": [handler_name],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": [handler_name],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    bind = options.get("bind", DEFAULT_BIND)
    host, port = bind.rsplit(":", 1)

    uvicorn.run(
        get_asgi_application(),
        host=host,
        port=int(port),
        log_config=logging_config,
    )
