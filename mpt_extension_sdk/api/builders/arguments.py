import re
from inspect import signature
from json import JSONDecodeError
from typing import Any

from fastapi import Request
from pydantic import ValidationError as PydanticValidationError

from mpt_extension_sdk.api.context import APIContext
from mpt_extension_sdk.api.error_mapping import PydanticValidationErrorMapper
from mpt_extension_sdk.api.errors import ValidationError
from mpt_extension_sdk.api.models.errors import ErrorDetail
from mpt_extension_sdk.routing.models import APIRouteDefinition


class APIHandlerArgumentsBuilder:
    """Build the arguments passed to authenticated API handlers."""

    _path_parameter_pattern = re.compile(r"\{([^:}]+)(?::[^}]+)?\}")

    def __init__(self, route: APIRouteDefinition) -> None:
        self._route = route
        self.context_parameter_name = self.resolve_context_parameter_name(route)
        self.body_parameter_name = self.resolve_body_parameter_name(
            route, self.context_parameter_name
        )

    @classmethod
    def extract_path_parameter_names(cls, path: str) -> list[str]:
        """Extract path parameter names from a FastAPI route path."""
        return cls._path_parameter_pattern.findall(path)

    @classmethod
    async def parse_request_body(cls, request: Request) -> Any:
        """Parse the incoming JSON payload when the request has a body."""
        raw_body = await request.body()
        if not raw_body:
            return None
        try:
            return await request.json()
        except JSONDecodeError as error:
            raise ValidationError(
                errors=[ErrorDetail(pointer="#", detail="Invalid JSON payload")]
            ) from error

    @classmethod
    def resolve_body_parameter_name(  # noqa: WPS231
        cls, route: APIRouteDefinition, context_parameter_name: str
    ) -> str | None:
        """Resolve the handler parameter that should receive the validated body."""
        body_validator_type = route.body_validator_type
        if body_validator_type is None:
            return None

        path_parameters = set(cls.extract_path_parameter_names(route.path))
        callback_parameters = list(signature(route.callback).parameters.values())
        for parameter in callback_parameters:
            if parameter.name in path_parameters or parameter.name == context_parameter_name:
                continue
            if parameter.annotation is body_validator_type:
                return parameter.name

        remaining_parameters = [
            callback_parameter.name
            for callback_parameter in callback_parameters
            if callback_parameter.name not in path_parameters
            and callback_parameter.name != context_parameter_name
        ]
        if len(remaining_parameters) == 1:
            return remaining_parameters[0]

        raise TypeError(
            "API handlers that declare a body validator must expose exactly one body parameter"
        )

    @classmethod
    def resolve_context_parameter_name(cls, route: APIRouteDefinition) -> str:
        """Resolve the handler parameter name that should receive the API context."""
        for parameter in signature(route.callback).parameters.values():
            if parameter.name in {"ctx", "context"}:
                return parameter.name
            if parameter.annotation is APIContext:
                return parameter.name
        raise TypeError("API handlers must declare a 'ctx' or 'context' parameter")

    @classmethod
    def validate_request_body(cls, payload: Any, body_validator_type: type[Any]) -> Any:
        """Validate the incoming JSON payload against the configured schema."""
        if payload is None:
            payload = {}
        try:
            return body_validator_type.model_validate(payload)
        except PydanticValidationError as error:
            raise ValidationError(errors=PydanticValidationErrorMapper.map(error)) from error

    async def build(self, *, request: Request, context: APIContext) -> dict[str, Any]:
        """Build the argument mapping passed to the extension handler."""
        handler_arguments = dict(request.path_params)
        handler_arguments[self.context_parameter_name] = context
        if self._route.body_validator_type is not None and self.body_parameter_name is not None:
            request_body = self.validate_request_body(
                context.request.body, self._route.body_validator_type
            )
            handler_arguments[self.body_parameter_name] = request_body
        return handler_arguments
