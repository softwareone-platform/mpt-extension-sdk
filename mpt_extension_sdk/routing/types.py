from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mpt_extension_sdk.routing.plugs import NavigationPlug, Plug

RouteCallback = Callable[..., Awaitable[Any] | Any]
EventRouteCallback = Callable[..., Awaitable[None] | None]
APIRouteCallback = Callable[..., Awaitable[object] | object]
PlugRouteCallback = Callable[[], Sequence["Plug | NavigationPlug"]]
