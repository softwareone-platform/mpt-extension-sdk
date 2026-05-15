from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mpt_extension_sdk.routing.plugs import Plug

RouteCallback = Callable[..., Awaitable[Any] | Any]
EventRouteCallback = Callable[..., Awaitable[None] | None]
APIRouteCallback = Callable[..., Awaitable[object] | object]
PlugRouteCallback = Callable[[], list["Plug"]]
