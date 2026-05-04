import logging
from dataclasses import dataclass
from typing import Any, Self

from mpt_extension_sdk.api.auth import AuthContext, AuthenticatedRequestContext
from mpt_extension_sdk.api.context import APIContext
from mpt_extension_sdk.api.models.events import Event
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.event import EventBaseContext, EventMetadata
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.runtime.logging import correlation_id_ctx, task_id_ctx
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService, MPTAPIServiceFactory
from mpt_extension_sdk.settings.extension import BaseExtensionSettings, get_extension_settings
from mpt_extension_sdk.settings.runtime import RuntimeSettings, get_runtime_settings


@dataclass
class RouteContextFactory:
    """Factory for building execution contexts across route families."""

    service_factory: MPTAPIServiceFactory
    runtime_settings: RuntimeSettings
    extension_settings: BaseExtensionSettings

    def build_api_context(
        self,
        *,
        auth_context: AuthContext,
        request_context: AuthenticatedRequestContext,
        handler_logger: logging.Logger,
    ) -> APIContext:
        """Build the authenticated execution context for an API request."""
        return APIContext(
            logger=handler_logger,
            mpt_api_service=self.service_factory.build_account_scoped_service(
                auth_context.account.id
            ),
            ext_settings=self.extension_settings,
            runtime_settings=self.runtime_settings,
            auth=auth_context,
            request=request_context,
        )

    async def build_event_context(
        self, event: Event, handler_logger: logging.Logger
    ) -> EventBaseContext:
        """Build the fully hydrated execution context for an incoming event."""
        api_service = self.service_factory.build_runtime_service()
        return await self._build_event_context_with_model(event, handler_logger, api_service)

    @classmethod
    def from_service_type(cls, mpt_api_service_type: type[MPTAPIService] = MPTAPIService) -> Self:
        """Build a route context factory using process-wide runtime settings."""
        runtime_settings = get_runtime_settings()
        return cls(
            service_factory=MPTAPIServiceFactory(
                runtime_settings=runtime_settings, service_type=mpt_api_service_type
            ),
            runtime_settings=runtime_settings,
            extension_settings=get_extension_settings(),
        )

    async def _build_event_context_with_model(
        self, event: Event, handler_logger: logging.Logger, api_service: MPTAPIService
    ) -> EventBaseContext:
        """Build a fully hydrated execution context for the current event object."""
        common_kwargs: dict[str, Any] = {
            "logger": handler_logger,
            "meta": self._build_execution_metadata(event),
            "mpt_api_service": api_service,
            "account_settings": None,
            "ext_settings": self.extension_settings,
            "runtime_settings": self.runtime_settings,
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


async def build_context(
    event: Event,
    handler_logger: logging.Logger,
    mpt_api_service_type: type[MPTAPIService] = MPTAPIService,
) -> EventBaseContext:
    """Build the fully hydrated execution context for an incoming event."""
    return await RouteContextFactory.from_service_type(mpt_api_service_type).build_event_context(
        event, handler_logger
    )


def build_api_context(
    *,
    auth_context: AuthContext,
    request_context: AuthenticatedRequestContext,
    handler_logger: logging.Logger,
    mpt_api_service_type: type[MPTAPIService] = MPTAPIService,
) -> APIContext:
    """Build the authenticated execution context for an API request."""
    return RouteContextFactory.from_service_type(mpt_api_service_type).build_api_context(
        auth_context=auth_context,
        request_context=request_context,
        handler_logger=handler_logger,
    )
