from typing import override

from mpt_extension_sdk.pipeline import BaseStep, OrderContext


class DemoStep(BaseStep):
    """Demo step."""

    @override
    async def process(self, ctx: OrderContext) -> None:  # type: ignore[override]
        ctx.logger.info("Demo step executed")
