from typing import override

from mock_app.context import MockContext
from mpt_extension_sdk.pipeline import BaseStep


class DemoStep(BaseStep):
    """Demo step."""

    @override
    async def process(self, ctx: MockContext) -> None:
        ctx.logger.info("Mock field %s", ctx.mock_field)
