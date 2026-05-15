from collections.abc import Awaitable, Callable
from typing import Any

RouteCallback = Callable[..., Awaitable[Any] | Any]
EventRouteCallback = Callable[..., Awaitable[None] | None]
APIRouteCallback = Callable[..., Awaitable[object] | object]
