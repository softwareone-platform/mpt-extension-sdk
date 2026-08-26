import inspect
import logging
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from mpt_extension_sdk.extension_validator import ExtensionValidator
from mpt_extension_sdk.routing import BaseRouteDefinition, EventRouteDefinition
from mpt_extension_sdk.routing.routers.base import BaseExtensionRouter
from mpt_extension_sdk.routing.validators import RouteValidator
from mpt_extension_sdk.runtime.builders import MetaConfigBuilder
from mpt_extension_sdk.runtime.models import MetaConfig
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService

logger = logging.getLogger(__name__)

type StartupHook = Callable[[], Awaitable[None] | None]


@dataclass
class StartupHooks:
    """Runtime startup hooks registered by an extension."""

    _hooks: list[StartupHook] = field(default_factory=list, repr=False)

    def __iter__(self) -> Iterator[StartupHook]:
        """Iterate the registered hooks in registration order."""
        return iter(self._hooks)

    def __len__(self) -> int:
        """The number of registered hooks."""
        return len(self._hooks)

    def register(self, hook: StartupHook) -> StartupHook:
        """Register a startup hook.

        Args:
            hook: Zero-argument callable, optionally a coroutine function.

        Returns:
            The registered hook, so registration can be used as a decorator.

        Raises:
            TypeError: If the hook is not callable.
        """
        if not callable(hook):
            raise TypeError("Startup hook must be callable")

        self._hooks.append(hook)
        return hook

    async def run(self) -> None:
        """Run the registered hooks sequentially in registration order.

        Running in registration order means a hook can rely on the
        initialization done by the hooks registered before it.
        """
        for hook in self._hooks:
            logger.info("Running extension startup hook '%s'", getattr(hook, "__name__", hook))
            outcome = hook()
            if inspect.isawaitable(outcome):
                await outcome  # noqa: WPS476


@dataclass
class ExtensionApp:
    """Explicit SDK integration object for an extension."""

    prefix: str = ""
    version: str = "6.0.0"
    openapi: str = "/bypass/openapi.json"
    mpt_api_service_type: type[MPTAPIService] = field(default=MPTAPIService)
    _routes: list[BaseRouteDefinition] = field(default_factory=list, init=False, repr=False)
    _startup_hooks: StartupHooks = field(default_factory=StartupHooks, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate extension app settings."""
        ExtensionValidator.validate_service_type(self.mpt_api_service_type)

    @property
    def routes(self) -> list[BaseRouteDefinition]:
        """The registered route definitions."""
        return list(self._routes)

    @property
    def startup_hooks(self) -> StartupHooks:
        """The registered runtime startup hooks."""
        return self._startup_hooks

    def on_startup(self, hook: StartupHook) -> StartupHook:
        """Register a hook to run when the runtime server starts.

        Hooks run once per served process, after observability is bootstrapped
        and before the app reports itself as ready. Metadata generation never
        invokes them. Usable as a decorator; sync and async hooks are both
        supported.

        Args:
            hook: Zero-argument callable, optionally a coroutine function.

        Returns:
            The registered hook, so the method can be used as a decorator.

        Raises:
            TypeError: If the hook is not callable.
        """
        return self._startup_hooks.register(hook)

    def build_context(self, route: EventRouteDefinition, context: Any) -> Any:
        """Adapt a base SDK context to the route-specific custom context."""
        adapter_type = route.context_adapter_type
        if adapter_type is None:
            return context

        ExtensionValidator.validate_context_adapter_for_context(adapter_type, context)
        adapted_context = adapter_type.from_context(context)
        expected_type = adapter_type.__name__
        if not isinstance(adapted_context, adapter_type):
            raise TypeError(f"{expected_type}.from_context must return {expected_type}")

        return adapted_context

    def include_router(self, router: BaseExtensionRouter) -> None:
        """Include a router in the extension app."""
        for route in router.prefixed_routes(self.prefix):
            RouteValidator.validate_route_uniqueness(route=route, routes=self._routes)
            self._routes.append(route)

    def to_meta_config(self) -> MetaConfig:
        """Build extension metadata from the registered application routes."""
        return MetaConfigBuilder(openapi=self.openapi, routes=self._routes).build()
