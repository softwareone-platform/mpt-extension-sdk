import json
import os
import sys
from importlib.metadata import entry_points
from pathlib import Path

from django.apps import apps
from django.contrib import admin
from django.urls import path
from django.utils.module_loading import import_string
from pyfiglet import Figlet
from rich.console import Console
from rich.text import Text

from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
    GRADIENT_HEX_BASE,
)
from mpt_extension_sdk.runtime.errors import VariableNotWellFormedError


def get_extension_app_config_name(
    group=DEFAULT_APP_CONFIG_GROUP, name=DEFAULT_APP_CONFIG_NAME
):
    """Get the extension app config name for the specified group and name."""
    eps = entry_points()
    (app_config_ep,) = eps.select(group=group, name=name)
    app_config = app_config_ep.load()
    return f"{app_config.__module__}.{app_config.__name__}"


def get_extension_app_config(
    group=DEFAULT_APP_CONFIG_GROUP, name=DEFAULT_APP_CONFIG_NAME
):
    """Get the extension app config for the specified group and name."""
    app_config_name = get_extension_app_config_name(group=group, name=name)
    return next(
        filter(
            lambda app: app_config_name
            == get_app_name(app),
            apps.app_configs.values(),
        ),
        None,
    )


def get_app_name(app):
    """Get the app name for the specified app."""
    return f"{app.__class__.__module__}.{app.__class__.__name__}"


def get_extension(group=DEFAULT_APP_CONFIG_GROUP, name=DEFAULT_APP_CONFIG_NAME):
    """Get the extension for the specified group and name."""
    return get_extension_app_config(group=group, name=name).extension


def get_events_registry(group=DEFAULT_APP_CONFIG_GROUP, name=DEFAULT_APP_CONFIG_NAME):
    """Get the events registry for the extension."""
    return get_extension(group=group, name=name).events


def gradient(start_hex, end_hex, num_samples=10):  # pragma: no cover
    """Retrieve the gradient."""
    start_rgb = tuple(int(start_hex[idx : idx + 2], GRADIENT_HEX_BASE) for idx in range(1, 6, 2))
    end_rgb = tuple(int(end_hex[idx : idx + 2], GRADIENT_HEX_BASE) for idx in range(1, 6, 2))
    gradient_colors = [start_hex]
    for sample in range(1, num_samples):
        red = int(
            start_rgb[0]
            + (float(sample) / (num_samples - 1)) * (end_rgb[0] - start_rgb[0])
        )
        green = int(
            start_rgb[1]
            + (float(sample) / (num_samples - 1)) * (end_rgb[1] - start_rgb[1])
        )
        blue = int(
            start_rgb[2]
            + (float(sample) / (num_samples - 1)) * (end_rgb[2] - start_rgb[2])
        )
        gradient_colors.append(f"#{red:02X}{green:02X}{blue:02X}")

    return gradient_colors


def show_banner():  # pragma: no cover
    """Show the banner."""
    program_name = Path(sys.argv[0]).name
    program_name = "".join((program_name[0:3].upper(), program_name[3:]))
    figlet = Figlet("georgia11")

    banner_text = figlet.renderText(program_name)

    banner_lines = [Text(line) for line in banner_text.splitlines()]
    max_line_length = max(len(line) for line in banner_lines)
    half_length = max_line_length // 2

    colors = gradient("#00C9CD", "#472AFF", half_length) + gradient(
        "#472AFF", "#392D9C", half_length + 1
    )
    console = Console()

    for line in banner_lines:
        colored_line = Text()
        for idx, line_char in enumerate(line):
            char = Text(line_char)
            char.stylize(colors[idx])
            colored_line = Text.assemble(colored_line, char)
        console.print(colored_line)


def get_extension_variables(json_ext_variables):
    """Get the extension variables from the environment."""
    variables = {}
    for var in filter(lambda ext_item: ext_item[0].startswith("EXT_"), os.environ.items()):
        if var[0] in json_ext_variables:
            try:
                item_value = json.loads(var[1])
            except json.JSONDecodeError:
                raise VariableNotWellFormedError(f"Variable {var[0]} not well formatted")
        else:
            item_value = var[1]

        variables[var[0][4:]] = item_value
    return variables


def get_api_url(extension):
    """Get the API URL for the extension."""
    if extension:
        return extension.api.urls
    return None


def get_urlpatterns(extension):
    """Get the URL patterns for the extension."""
    urlpatterns = [
        path("admin/", admin.site.urls),
    ]

    api_url = get_api_url(extension)

    if api_url:
        urlpatterns.append(path("api/", api_url))

    return urlpatterns


def get_initializer_function():
    """Dynamically import and return the initializer function from settings.INITIALIZER."""
    # Read from environment variable instead of Django settings to avoid circular dependency
    # (Django settings need to be configured before we can read settings.INITIALIZER)
    return os.getenv(
        "MPT_INITIALIZER", "mpt_extension_sdk.runtime.initializer.initialize"
    )


def initialize_extension(
    options, group=DEFAULT_APP_CONFIG_GROUP, name=DEFAULT_APP_CONFIG_NAME
):
    """Initialize the extension."""
    initialize_path = get_initializer_function()
    initialize_func = import_string(initialize_path)
    initialize_func(options, group=group, name=name)
