import warnings
from collections.abc import Callable
from dataclasses import dataclass

from mpt_extension_sdk.routing.enums import HTTPMethod, RouteType
from mpt_extension_sdk.routing.models import APIRouteDefinition, TaskTimeouts
from mpt_extension_sdk.routing.routers.base import BaseExtensionRouter
from mpt_extension_sdk.routing.types import APIRouteCallback
from mpt_extension_sdk.routing.validators import RouteValidator
from mpt_extension_sdk.schemas import BaseSchema


@dataclass
class APIRouter(BaseExtensionRouter):
    """Router object for authenticated API endpoints."""

    def delete(
        self,
        path: str,
        name: str,
        body_validator: type[BaseSchema] | None = None,
        *,
        deferrable: bool = False,
        timeouts: TaskTimeouts | None = None,
    ) -> Callable[[APIRouteCallback], APIRouteCallback]:
        """Register an authenticated DELETE handler."""
        return self._create_api_decorator(
            method=HTTPMethod.DELETE,
            path=path,
            name=name,
            body_validator=body_validator,
            deferrable=deferrable,
            timeouts=timeouts,
        )

    def endpoint(self, path: str, name: str) -> Callable[[APIRouteCallback], APIRouteCallback]:
        """Register an authenticated GET handler.

        Deprecated: use ``get`` instead. ``endpoint`` supports neither a body
        validator nor a deferrable endpoint.
        """
        warnings.warn(
            "APIRouter.endpoint is deprecated, use APIRouter.get instead: endpoint "
            "supports neither a body validator nor a deferrable endpoint",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get(path=path, name=name)

    def get(
        self,
        path: str,
        name: str,
        body_validator: type[BaseSchema] | None = None,
        *,
        deferrable: bool = False,
        timeouts: TaskTimeouts | None = None,
    ) -> Callable[[APIRouteCallback], APIRouteCallback]:
        """Register an authenticated GET handler."""
        return self._create_api_decorator(
            method=HTTPMethod.GET,
            path=path,
            name=name,
            body_validator=body_validator,
            deferrable=deferrable,
            timeouts=timeouts,
        )

    def patch(
        self,
        path: str,
        name: str,
        body_validator: type[BaseSchema] | None = None,
        *,
        deferrable: bool = False,
        timeouts: TaskTimeouts | None = None,
    ) -> Callable[[APIRouteCallback], APIRouteCallback]:
        """Register an authenticated PATCH handler."""
        return self._create_api_decorator(
            method=HTTPMethod.PATCH,
            path=path,
            name=name,
            body_validator=body_validator,
            deferrable=deferrable,
            timeouts=timeouts,
        )

    def post(
        self,
        path: str,
        name: str,
        body_validator: type[BaseSchema] | None = None,
        *,
        deferrable: bool = False,
        timeouts: TaskTimeouts | None = None,
    ) -> Callable[[APIRouteCallback], APIRouteCallback]:
        """Register an authenticated POST handler."""
        return self._create_api_decorator(
            method=HTTPMethod.POST,
            path=path,
            name=name,
            body_validator=body_validator,
            deferrable=deferrable,
            timeouts=timeouts,
        )

    def put(
        self,
        path: str,
        name: str,
        body_validator: type[BaseSchema] | None = None,
        *,
        deferrable: bool = False,
        timeouts: TaskTimeouts | None = None,
    ) -> Callable[[APIRouteCallback], APIRouteCallback]:
        """Register an authenticated PUT handler."""
        return self._create_api_decorator(
            method=HTTPMethod.PUT,
            path=path,
            name=name,
            body_validator=body_validator,
            deferrable=deferrable,
            timeouts=timeouts,
        )

    def _create_api_decorator(  # noqa: WPS211
        self,
        *,
        method: HTTPMethod,
        path: str,
        name: str,
        body_validator: type[BaseSchema] | None,
        deferrable: bool,
        timeouts: TaskTimeouts | None,
    ) -> Callable[[APIRouteCallback], APIRouteCallback]:
        """Create a decorator for an authenticated API route."""
        normalized_path = self._join_paths(self.prefix, path)
        RouteValidator.validate_body_validator_type(body_validator)
        RouteValidator.validate_deferrable_options(
            path=normalized_path, deferrable=deferrable, timeouts=timeouts
        )

        def decorator(route_handler: APIRouteCallback) -> APIRouteCallback:
            RouteValidator.validate_deferrable_handler(route_handler, deferrable=deferrable)
            self._register_base_route(
                APIRouteDefinition(
                    name=name,
                    path=normalized_path,
                    route_type=RouteType.API,
                    callback=route_handler,
                    method=method,
                    body_validator_type=body_validator,
                    deferrable=deferrable,
                    timeouts=timeouts,
                )
            )
            return route_handler

        return decorator
