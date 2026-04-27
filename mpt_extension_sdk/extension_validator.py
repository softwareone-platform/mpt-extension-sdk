from typing import TYPE_CHECKING

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.services.mpt_api_service.api_service import MPTAPIService

if TYPE_CHECKING:
    from mpt_extension_sdk.pipeline import EventBaseContext
    from mpt_extension_sdk.routing.models import BaseRouteDefinition


class ExtensionValidator:
    """Validation helpers for the `ExtensionApp` contract."""

    @classmethod
    def validate_service_type(cls, service_type: type[object]) -> None:
        """Validate that the configured API service type is supported."""
        if not issubclass(service_type, MPTAPIService):
            raise TypeError("mpt_api_service_type must inherit from MPTAPIService")

    @classmethod
    def validate_context_adapter_type(cls, context_type: type[object] | None) -> None:
        """Validate a configured custom context adapter type."""
        if context_type is None:
            return
        if not issubclass(context_type, ContextAdapter):
            raise TypeError(
                f"Configured context type '{context_type.__name__}' must implement "
                f"'{ContextAdapter.__name__}'"
            )

    @classmethod
    def validate_context_adapter_for_context(
        cls, context_type: type[ContextAdapter], context: "EventBaseContext"
    ) -> None:
        """Validate that a configured adapter matches the context family."""
        if isinstance(context, OrderContext) and not issubclass(context_type, OrderContext):
            raise TypeError(
                f"Configured context type '{context_type.__name__}' must inherit from "
                f"'{OrderContext.__name__}'"
            )
        if isinstance(context, AgreementContext) and not issubclass(context_type, AgreementContext):
            raise TypeError(
                f"Configured context type '{context_type.__name__}' must inherit from "
                f"'{AgreementContext.__name__}'"
            )

    @classmethod
    def validate_route_uniqueness(
        cls, *, route: "BaseRouteDefinition", routes: list["BaseRouteDefinition"]
    ) -> None:
        """Validate that a route name and path are unique within a route list."""
        if any(existing_route.name == route.name for existing_route in routes):
            raise ValueError(f"Route name '{route.name}' is already registered")
        if any(existing_route.path == route.path for existing_route in routes):
            raise ValueError(f"Route path '{route.path}' is already registered")
        if route.route_type == "event" and any(
            existing_route.route_type == "event"
            and getattr(existing_route, "event", None) == getattr(route, "event", None)
            for existing_route in routes
        ):
            raise ValueError(f"Route event '{getattr(route, 'event', '')}' is already registered")
