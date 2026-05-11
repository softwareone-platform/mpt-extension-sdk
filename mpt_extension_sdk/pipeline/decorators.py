from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, Concatenate, cast

from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.pipeline.step import BaseStep

type StepCallable[StepT: BaseStep, CtxT: OrderContext, ReturnT, **ParamT] = Callable[
    Concatenate[StepT, CtxT, ParamT], Coroutine[Any, Any, ReturnT]
]


def refresh_order[StepT: BaseStep, CtxT: OrderContext, ReturnT, **ParamT](
    func: StepCallable[StepT, CtxT, ReturnT, ParamT],
) -> StepCallable[StepT, CtxT, ReturnT, ParamT]:
    """Refresh the order context after a successful step method."""

    @wraps(func)
    async def wrapper(
        self: StepT, ctx: CtxT, *args: ParamT.args, **kwargs: ParamT.kwargs
    ) -> ReturnT:
        result = await func(self, ctx, *args, **kwargs)
        await ctx.refresh_order()
        return result

    return cast(StepCallable[StepT, CtxT, ReturnT, ParamT], wrapper)
