from collections.abc import Awaitable
from functools import wraps
from typing import Any, cast

from mpt_extension_sdk.routing.types import APIRouteCallback

_ONLY_DEFERRABLE_MARKER = "_mpt_only_deferrable"


def only_deferrable(route_handler: APIRouteCallback) -> APIRouteCallback:
    """Restrict an API handler to deferred delivery.

    Apply it below the `APIRouter` method decorator. The route is then deferrable
    without `deferrable=True`, and a direct call is answered with
    `405 Method Not Allowed` instead of running the handler.

    The handler itself is left unchanged, so it can still be registered on another
    route that accepts both call modes.

    Args:
        route_handler: Deferrable API handler, always a coroutine function.

    Returns:
        A wrapper that calls the handler, marked as deferred only.
    """

    @wraps(route_handler)
    async def only_deferrable_handler(*args: Any, **kwargs: Any) -> object:  # noqa: WPS430
        return await cast(Awaitable[object], route_handler(*args, **kwargs))

    setattr(only_deferrable_handler, _ONLY_DEFERRABLE_MARKER, True)
    return only_deferrable_handler


def is_only_deferrable(route_handler: APIRouteCallback) -> bool:
    """Return whether an API handler is restricted to deferred delivery."""
    return getattr(route_handler, _ONLY_DEFERRABLE_MARKER, False) is True
