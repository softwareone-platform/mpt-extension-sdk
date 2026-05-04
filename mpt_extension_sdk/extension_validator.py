from typing import TYPE_CHECKING

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.pipeline import AgreementContext, OrderContext
from mpt_extension_sdk.routing.enums import RouteType
from mpt_extension_sdk.routing.models import BaseRouteDefinition
from mpt_extension_sdk.schemas import BaseSchema
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService

if TYPE_CHECKING:
    from mpt_extension_sdk.pipeline import EventBaseContext


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
    def validate_body_validator_type(cls, schema_type: type[object] | None) -> None:
        """Validate a configured request body validator type."""
        if schema_type is None:
            return
        if not issubclass(schema_type, BaseSchema):
            raise TypeError(
                f"Configured body validator type '{schema_type.__name__}' must inherit "
                f"from '{BaseSchema.__name__}'"
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
        cls, *, route: BaseRouteDefinition, routes: list[BaseRouteDefinition]
    ) -> None:
        """Validate that a route name and path are unique within a route list."""
        if any(existing_route.name == route.name for existing_route in routes):
            raise ValueError(f"Route name '{route.name}' is already registered")

        existing_path_routes = [
            existing_route for existing_route in routes if existing_route.path == route.path
        ]
        if route.route_type == RouteType.API:
            cls._validate_api_route_uniqueness(route, existing_path_routes)
            return
        if existing_path_routes:
            raise ValueError(f"Route path '{route.path}' is already registered")
        if route.route_type == RouteType.EVENT and any(
            existing_route.route_type == RouteType.EVENT
            and getattr(existing_route, "event", None) == getattr(route, "event", None)
            for existing_route in routes
        ):
            raise ValueError(f"Route event '{getattr(route, 'event', '')}' is already registered")

    @classmethod
    def _validate_api_route_uniqueness(
        cls, route: BaseRouteDefinition, existing_path_routes: list[BaseRouteDefinition]
    ) -> None:
        """Validate that an API route does not collide with already registered routes."""
        if any(
            existing_route.route_type != RouteType.API for existing_route in existing_path_routes
        ):
            raise ValueError(f"Route path '{route.path}' is already registered")
        if any(
            getattr(existing_route, "method", None) == getattr(route, "method", None)
            for existing_route in existing_path_routes
        ):
            method = getattr(route, "method", "")
            raise ValueError(
                f"Route path '{route.path}' is already registered for method '{method}'"
            )
