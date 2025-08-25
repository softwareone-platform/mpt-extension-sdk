from contextlib import nullcontext

import click
from django.core.management import execute_from_command_line
from opentelemetry import trace

from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
    DJANGO_SETTINGS_MODULE,
)
from mpt_extension_sdk.runtime.utils import initialize_extension


@click.command(
    add_help_option=False,
    context_settings={"ignore_unknown_options": True},
)
@click.argument("management_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def django(ctx, management_args):  # pragma: no cover
    """Execute Django subcommands."""
    from django.conf import settings  # noqa: PLC0415

    options = {
        "group": DEFAULT_APP_CONFIG_GROUP,
        "name": DEFAULT_APP_CONFIG_NAME,
        "django_settings_module": DJANGO_SETTINGS_MODULE,
    }

    initialize_extension(options=options)

    if settings.USE_APPLICATIONINSIGHTS:
        tracer = trace.get_tracer(__name__)
        tracer_context = tracer.start_as_current_span(
            f"Running Django command {management_args[0]}",
        )
    else:
        tracer_context = nullcontext()

    with tracer_context:
        execute_from_command_line(argv=[ctx.command_path, *management_args])
