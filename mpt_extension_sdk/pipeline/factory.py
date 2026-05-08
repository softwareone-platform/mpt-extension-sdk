import logging
from typing import Any

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.api.models.events import Event
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.event import EventBaseContext, EventMetadata
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.runtime.logging import correlation_id_ctx, task_id_ctx
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.extension import get_extension_settings
from mpt_extension_sdk.settings.runtime import get_runtime_settings


async def build_context(
    event: Event,
    handler_logger: logging.Logger,
    *,
    auth: AuthContext,
    mpt_api_service_type: type[MPTAPIService] = MPTAPIService,
) -> EventBaseContext:
    """Build the fully hydrated execution context for an incoming event."""
    runtime_settings = get_runtime_settings()
    api_service = await mpt_api_service_type.from_auth_context(
        base_url=runtime_settings.mpt_api_base_url,
        auth=auth,
    )
    return await _build_context_with_model(event, handler_logger, api_service, auth=auth)


def _build_execution_metadata(event: Event) -> EventMetadata:
    """Build immutable execution metadata from the incoming event."""
    return EventMetadata(
        event_id=event.id,
        object_id=event.object.id,
        object_type=event.object.object_type,
        correlation_id=correlation_id_ctx.get(),
        task_id=task_id_ctx.get(),
    )


async def _build_context_with_model(
    event: Event,
    handler_logger: logging.Logger,
    api_service: MPTAPIService,
    auth: AuthContext | None = None,
) -> EventBaseContext:
    """Build a fully hydrated execution context for the current event object."""
    common_kwargs: dict[str, Any] = {
        "logger": handler_logger,
        "meta": _build_execution_metadata(event),
        "mpt_api_service": api_service,
        "account_settings": None,
        "ext_settings": get_extension_settings(),
        "runtime_settings": get_runtime_settings(),
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
