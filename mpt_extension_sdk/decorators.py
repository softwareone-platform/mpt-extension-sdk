from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService

DEFAULT_OPS_ACCOUNT_ID_SETTING = "mpt_ops_account_id"

type HandlerCallable[**ParamT, ReturnT] = Callable[ParamT, Coroutine[Any, Any, ReturnT]]


def with_operations_mpt_api_service(
    *,
    settings_attr: str = DEFAULT_OPS_ACCOUNT_ID_SETTING,
    service_type: type[MPTAPIService] = MPTAPIService,
) -> Callable[[HandlerCallable[..., Any]], HandlerCallable[..., Any]]:
    """Attach an Operations-authenticated MPTAPIService to the handler context.

    Reads the configured Operations account id from
    ``ctx.ext_settings.<settings_attr>`` (default ``mpt_ops_account_id``),
    builds an account-scoped ``MPTAPIService`` via
    ``MPTAPIService.from_account_id`` using the runtime MPT API base URL, and
    assigns it to ``ctx.ops_mpt_api_service`` before invoking the wrapped
    handler. ``ctx.mpt_api_service`` is left untouched.

    The wrapped handler must receive a ``BaseContext``-derived instance among
    its arguments (event handlers receive it as the second positional argument
    ``(event, ctx)``; pipeline step methods receive it as ``(self, ctx, ...)``).

    Args:
        settings_attr: Name of the extension-settings attribute holding the
            Operations account id.
        service_type: ``MPTAPIService`` subclass to instantiate; defaults to
            the SDK ``MPTAPIService``.
    """

    def decorator(func: HandlerCallable[..., Any]) -> HandlerCallable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = _find_base_context(args, kwargs)
            account_id = getattr(ctx.ext_settings, settings_attr)
            ctx.ops_mpt_api_service = await service_type.from_account_id(
                base_url=ctx.runtime_settings.mpt_api_base_url,
                account_id=account_id,
            )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _find_base_context(args: tuple[Any, ...], kwargs: dict[str, Any]) -> BaseContext:
    for candidate in (*args, *kwargs.values()):
        if isinstance(candidate, BaseContext):
            return candidate
    raise TypeError(
        "with_operations_mpt_api_service requires a BaseContext argument in the wrapped handler"
    )
