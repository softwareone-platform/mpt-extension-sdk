import logging
from dataclasses import dataclass
from typing import Any, Self

from mpt_extension_sdk.api.auth import AuthContext, AuthenticationError
from mpt_extension_sdk.api.context import APIContext, AuthenticatedRequestContext
from mpt_extension_sdk.api.models.events import Event
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.event import EventBaseContext, EventMetadata
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.runtime.logging import correlation_id_ctx, task_id_ctx
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings, get_extension_settings
from mpt_extension_sdk.settings.runtime import RuntimeSettings, get_runtime_settings


@dataclass
class RouteContextFactory:
    """Factory for building execution contexts across route families."""

    runtime_settings: RuntimeSettings
    extension_settings: BaseExtensionSettings
    service_type: type[MPTAPIService] = MPTAPIService

    @classmethod
    def from_service_type(cls, service_type: type[MPTAPIService] = MPTAPIService) -> Self:
        """Build a route context factory using process-wide runtime settings."""
        return cls(
            runtime_settings=get_runtime_settings(),
            extension_settings=get_extension_settings(),
            service_type=service_type,
        )

    async def build_api_context(
        self,
        *,
        auth_context: AuthContext,
        request_context: AuthenticatedRequestContext,
        handler_logger: logging.Logger,
    ) -> APIContext:
        """Build the authenticated execution context for an API request."""
        self._assert_extension_id_matches(auth_context)
        api_service = await self.service_type.from_auth_context(
            base_url=self.runtime_settings.mpt_api_base_url,
            auth=auth_context,
        )
        return APIContext(
            logger=handler_logger,
            mpt_api_service=api_service,
            ext_settings=self.extension_settings,
            runtime_settings=self.runtime_settings,
            auth=auth_context,
            request=request_context,
        )

    async def build_event_context(
        self,
        event: Event,
        handler_logger: logging.Logger,
        auth: AuthContext,
    ) -> EventBaseContext:
        """Build the fully hydrated execution context for an incoming event."""
        self._assert_extension_id_matches(auth)
        api_service = await self.service_type.from_auth_context(
            base_url=self.runtime_settings.mpt_api_base_url,
            auth=auth,
        )
        return await self._build_event_context_with_model(
            event, handler_logger, api_service, auth=auth
        )

    def _assert_extension_id_matches(self, auth: AuthContext) -> None:
        """Ensure the incoming token targets the configured extension."""
        if auth.extension_id != self.runtime_settings.extension_id:
            raise AuthenticationError

    async def _build_event_context_with_model(
        self,
        event: Event,
        handler_logger: logging.Logger,
        api_service: MPTAPIService,
        auth: AuthContext,
    ) -> EventBaseContext:
        """Build a fully hydrated execution context for the current event object."""
        common_kwargs: dict[str, Any] = {
            "logger": handler_logger,
            "meta": self._build_execution_metadata(event),
            "mpt_api_service": api_service,
            "account_settings": None,
            "ext_settings": self.extension_settings,
            "runtime_settings": self.runtime_settings,
            "auth": auth,
        }

        object_type = event.object.object_type
        if object_type == "Order":
            order = await api_service.orders.get_by_id(event.object.id)
            return OrderContext(order=order, **common_kwargs)

        if object_type == "Agreement":
            agreement = await api_service.agreements.get_by_id(event.object.id)
            return AgreementContext(agreement=agreement, **common_kwargs)

        raise RuntimeError(f"Unsupported context type: {object_type}")

    def _build_execution_metadata(self, event: Event) -> EventMetadata:
        """Build immutable execution metadata from the incoming event."""
        return EventMetadata(
            event_id=event.id,
            object_id=event.object.id,
            object_type=event.object.object_type,
            correlation_id=correlation_id_ctx.get(),
            task_id=task_id_ctx.get(),
        )


async def build_api_context(
    *,
    auth_context: AuthContext,
    request_context: AuthenticatedRequestContext,
    handler_logger: logging.Logger,
    mpt_api_service_type: type[MPTAPIService] = MPTAPIService,
) -> APIContext:
    """Build the authenticated execution context for an API request."""
    return await RouteContextFactory.from_service_type(mpt_api_service_type).build_api_context(
        auth_context=auth_context,
        request_context=request_context,
        handler_logger=handler_logger,
    )


async def build_context(
    event: Event,
    handler_logger: logging.Logger,
    *,
    auth: AuthContext,
    mpt_api_service_type: type[MPTAPIService] = MPTAPIService,
) -> EventBaseContext:
    """Build the fully hydrated execution context for an incoming event."""
    return await RouteContextFactory.from_service_type(mpt_api_service_type).build_event_context(
        event,
        handler_logger,
        auth,
    )
