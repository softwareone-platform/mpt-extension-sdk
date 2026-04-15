from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.pipeline import AgreementContext, OrderContext


def get_context_by_type(model_type: str) -> type[OrderContext | AgreementContext]:
    """Return the context subclass matching the marketplace object type."""
    context_map = {
        "Agreement": AgreementContext,
        "Order": OrderContext,
    }
    try:
        return context_map[model_type]
    except KeyError as error:
        raise ConfigError(f"Unsupported object type: {model_type}") from error
