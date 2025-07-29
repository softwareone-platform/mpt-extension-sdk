import click
import debugpy  # noqa
from django.conf import settings

from mpt_extension_sdk.runtime.master import Master


@click.command()
@click.argument(
    "component",
    default="all",
    type=click.Choice(["all", "api", "consumer"]),
    metavar="[COMPONENT]",
)
@click.option("--color/--no-color", default=True)
@click.option("--debug", is_flag=True, default=False)
@click.option("--reload", is_flag=True, default=False)
@click.option("--debug-py", default=None)
def run(component, color, debug, reload, debug_py):
    """Run the extension.

    \b
    COMPONENT is the the name of the component to run. Possible values:
        * all - run both API and Event Consumer threads (default)
        * api - run only API thread
        * consumer - run only Event Consumer thread
    """

    if debug_py:
        host, port = debug_py.split(":")
        debugpy.listen((host, int(port)))  # noqa

    options = {
        "color": color,
        "debug": debug,
        "reload": reload,
        "component": component,
    }

    master = Master(
        options,
        settings=settings,
    )
    master.run()  # pragma: no cover
