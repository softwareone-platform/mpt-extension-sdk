import click

from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
    DJANGO_SETTINGS_MODULE,
)
from mpt_extension_sdk.runtime.initializer import initialize
from mpt_extension_sdk.runtime.tracer import dynamic_trace_span


@dynamic_trace_span(lambda *args: f"Running Django command {args[1]}")
def execute(ctx, management_args):
    from django.core.management import execute_from_command_line

    execute_from_command_line(argv=[ctx.command_path] + list(management_args))


@click.command(
    add_help_option=False,
    context_settings={"ignore_unknown_options": True},
)
@click.argument("management_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def django(ctx, management_args):  # pragma: no cover
    """Execute Django subcommands."""
    initialize(
        {
            "group": DEFAULT_APP_CONFIG_GROUP,
            "name": DEFAULT_APP_CONFIG_NAME,
            "django_settings_module": DJANGO_SETTINGS_MODULE,
        }
    )

    execute(ctx, management_args)
