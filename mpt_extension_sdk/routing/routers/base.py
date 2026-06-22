from dataclasses import dataclass, field

from mpt_extension_sdk.extension_validator import ExtensionValidator
from mpt_extension_sdk.routing import BaseRouteDefinition


@dataclass
class BaseExtensionRouter:
    """Shared router behavior for extension route families."""

    prefix: str = ""
    _routes: list[BaseRouteDefinition] = field(default_factory=list, init=False, repr=False)

    @property
    def routes(self) -> list[BaseRouteDefinition]:
        """The registered route definitions."""
        return list(self._routes)

    def prefixed_routes(self, prefix: str) -> list[BaseRouteDefinition]:
        """Return route definitions with the given prefix applied to each path."""
        return [self._with_prefix(prefix, route) for route in self._routes]

    def _join_paths(self, prefix: str, path: str) -> str:
        """Join a router prefix and route path."""
        base = path.strip()
        if not base:
            raise ValueError("Route path cannot be empty")

        suffix = base if base.startswith("/") else f"/{base}"
        cleaned_prefix = prefix.strip()
        if not cleaned_prefix:
            return suffix

        normalized_prefix = (
            cleaned_prefix if cleaned_prefix.startswith("/") else f"/{cleaned_prefix}"
        )
        normalized_prefix = normalized_prefix.rstrip("/")
        if not normalized_prefix:
            return suffix

        return normalized_prefix if suffix == "/" else f"{normalized_prefix}{suffix}"

    def _with_prefix(self, prefix: str, route: BaseRouteDefinition) -> BaseRouteDefinition:
        """Return a copy of the route with the provided prefix applied."""
        route_payload = {**route.__dict__}
        route_payload["path"] = self._join_paths(prefix, route.path)
        return type(route)(**route_payload)

    def _register_base_route(self, route: BaseRouteDefinition) -> None:
        """Register a route definition on the router."""
        if not route.name.strip():
            raise ValueError("Route name cannot be empty")

        ExtensionValidator.validate_route_uniqueness(route=route, routes=self._routes)
        self._routes.append(route)
