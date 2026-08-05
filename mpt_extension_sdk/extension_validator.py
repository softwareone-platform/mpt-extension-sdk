from typing import TYPE_CHECKING

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.pipeline import AgreementContext, OrderContext
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService

if TYPE_CHECKING:
    from mpt_extension_sdk.pipeline import EventBaseContext


class ExtensionValidator:
    """Validation helpers for the `ExtensionApp` contract."""

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
    def validate_service_type(cls, service_type: type[object]) -> None:
        """Validate that the configured API service type is supported."""
        if not issubclass(service_type, MPTAPIService):
            raise TypeError("mpt_api_service_type must inherit from MPTAPIService")
