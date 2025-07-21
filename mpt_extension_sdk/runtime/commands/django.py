from contextlib import nullcontext

import click
from django.core.management import execute_from_command_line
from opentelemetry import trace

from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
    DJANGO_SETTINGS_MODULE,
)


@click.command(
    add_help_option=False,
    context_settings={"ignore_unknown_options": True},
)
@click.argument("management_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def django(ctx, management_args):  # pragma: no cover
    "Execute Django subcommands."
    import os

    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured

    from mpt_extension_sdk.runtime.utils import get_initializer_function

    # Call get_initializer_function() first to trigger module import and environment setup
    try:
        initialize = get_initializer_function()
    except ImproperlyConfigured as e:
        raise click.ClickException(f"Django configuration error: {e}")

    # Now check for Django settings after giving the initializer a chance to set it up
    if "DJANGO_SETTINGS_MODULE" not in os.environ:
        raise click.ClickException(
            "DJANGO_SETTINGS_MODULE environment variable is not set. "
            "Please set it to your Django settings module before running this command."
        )

    options = {
        "group": DEFAULT_APP_CONFIG_GROUP,
        "name": DEFAULT_APP_CONFIG_NAME,
        "django_settings_module": DJANGO_SETTINGS_MODULE,
    }

    initialize(options=options)

    if settings.USE_APPLICATIONINSIGHTS:
        tracer = trace.get_tracer(__name__)
        tracer_context = tracer.start_as_current_span(
            f"Running Django command {management_args[0]}",
        )
    else:
        tracer_context = nullcontext()

    with tracer_context:
        execute_from_command_line(argv=[ctx.command_path] + list(management_args))
