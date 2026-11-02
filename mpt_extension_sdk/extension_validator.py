from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.pipeline import AgreementContext, EventBaseContext, OrderContext
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.webhooks import WebhookContext


class ExtensionValidator:
    """Validation helpers for the `ExtensionApp` contract."""

    @classmethod
    def validate_context_adapter_for_context(
        cls, context_type: type[ContextAdapter], context: EventBaseContext | WebhookContext
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
        webhook_context_type = context.__class__
        if isinstance(context, WebhookContext) and not issubclass(
            context_type, webhook_context_type
        ):
            raise TypeError(
                f"Configured context type '{context_type.__name__}' must inherit from "
                f"'{webhook_context_type.__name__}'"
            )

    @classmethod
    def validate_service_type(cls, service_type: type[object]) -> None:
        """Validate that the configured API service type is supported."""
        if not issubclass(service_type, MPTAPIService):
            raise TypeError("mpt_api_service_type must inherit from MPTAPIService")
