import logging
from dataclasses import dataclass
from typing import Any, Self

from mpt_extension_sdk.api.auth import AuthContext, AuthenticationError
from mpt_extension_sdk.api.context import APIContext, AuthenticatedRequestContext
from mpt_extension_sdk.api.models.events import Event, TaskEvent
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.event import EventBaseContext, EventMetadata
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.pipeline.context.schedule import (
    ScheduleContext,
    ScheduleMetadata,
    ScheduleTaskHandle,
)
from mpt_extension_sdk.runtime.logging import correlation_id_ctx, task_id_ctx
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.task import TaskService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings, get_extension_settings
from mpt_extension_sdk.settings.runtime import RuntimeSettings, get_runtime_settings


@dataclass(frozen=True)
class ContextServices:
    """Marketplace services exposed to a single execution context."""

    mpt_api_service: MPTAPIService
    vendor_mpt_api_service: MPTAPIService


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
        services = await self._build_services(auth_context)
        return APIContext(
            logger=handler_logger,
            mpt_api_service=services.mpt_api_service,
            vendor_mpt_api_service=services.vendor_mpt_api_service,
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
        services = await self._build_services(auth)
        return await self._build_event_context_with_model(
            event, handler_logger, services, auth=auth
        )

    async def build_schedule_context(  # noqa: WPS211
        self,
        *,
        schedule_id: str,
        task_id: str,
        handler_logger: logging.Logger,
        auth: AuthContext,
        task_service: TaskService,
        event: TaskEvent,
    ) -> ScheduleContext:
        """Build the authenticated context for a schedule execution."""
        self._assert_extension_id_matches(auth)
        services = await self._build_services(auth)
        return ScheduleContext(
            logger=handler_logger,
            meta=ScheduleMetadata(
                enqueue_time=event.details.enqueue_time,
                event_id=event.id,
                schedule_id=schedule_id,
                task_id=task_id,
                correlation_id=correlation_id_ctx.get(),
            ),
            task=ScheduleTaskHandle(id=task_id, task_service=task_service),
            mpt_api_service=services.mpt_api_service,
            vendor_mpt_api_service=services.vendor_mpt_api_service,
            ext_settings=self.extension_settings,
            runtime_settings=self.runtime_settings,
            auth=auth,
        )

    async def _build_services(self, auth: AuthContext) -> ContextServices:
        """Build the account-scoped and vendor-scoped Marketplace services."""
        base_url = self.runtime_settings.mpt_api_base_url
        return ContextServices(
            mpt_api_service=await self.service_type.from_auth_context(base_url=base_url, auth=auth),
            vendor_mpt_api_service=await self.service_type.from_vendor_account(base_url=base_url),
        )

    def _assert_extension_id_matches(self, auth: AuthContext) -> None:
        """Ensure the incoming token targets the configured extension."""
        if auth.extension_id != self.runtime_settings.extension_id:
            raise AuthenticationError

    async def _build_event_context_with_model(
        self,
        event: Event,
        handler_logger: logging.Logger,
        services: ContextServices,
        auth: AuthContext,
    ) -> EventBaseContext:
        """Build a fully hydrated execution context for the current event object."""
        api_service = services.mpt_api_service
        common_kwargs: dict[str, Any] = {
            "logger": handler_logger,
            "meta": EventMetadata(
                event_id=event.id,
                object_id=event.object.id,
                object_type=event.object.object_type,
                correlation_id=correlation_id_ctx.get(),
                task_id=task_id_ctx.get(),
            ),
            "mpt_api_service": api_service,
            "vendor_mpt_api_service": services.vendor_mpt_api_service,
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
