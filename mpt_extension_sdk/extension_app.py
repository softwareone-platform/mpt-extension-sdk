from dataclasses import dataclass, field
from typing import Any

from mpt_extension_sdk.extension_validator import ExtensionValidator
from mpt_extension_sdk.routing import (
    BaseRouteDefinition,
    EventDeliveryMode,
    EventRouteDefinition,
)
from mpt_extension_sdk.routing.routers.base import BaseExtensionRouter
from mpt_extension_sdk.runtime.builders import PlugMetadataBuilder
from mpt_extension_sdk.runtime.models import MetaConfig, MetaEvent, MetaPlug
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService


@dataclass
class ExtensionApp:
    """Explicit SDK integration object for an extension."""

    prefix: str = ""
    version: str = "6.0.0"
    openapi: str = "/bypass/openapi.json"
    mpt_api_service_type: type[MPTAPIService] = field(default=MPTAPIService)
    _routes: list[BaseRouteDefinition] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate extension app settings."""
        ExtensionValidator.validate_service_type(self.mpt_api_service_type)

    @property
    def routes(self) -> list[BaseRouteDefinition]:
        """Return the registered route definitions."""
        return list(self._routes)

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
            ExtensionValidator.validate_route_uniqueness(route=route, routes=self._routes)
            self._routes.append(route)

    def to_meta_config(self) -> MetaConfig:
        """Build extension metadata from the registered application routes."""
        return MetaConfig(
            openapi=self.openapi,
            events=[
                MetaEvent(
                    event=route.event,
                    condition=route.condition,
                    path=route.path,
                    task=route.delivery_mode == EventDeliveryMode.TASK,
                )
                for route in self._routes
                if isinstance(route, EventRouteDefinition)
            ],
            plugs=self._build_meta_plugs() or None,
        )

    def _build_meta_plugs(self) -> list[MetaPlug]:
        """Build plug metadata from registered plug providers."""
        return PlugMetadataBuilder(routes=self._routes).build()
