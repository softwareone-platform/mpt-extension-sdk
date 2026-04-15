from typing import override

from mock_app.api.steps import DemoStep
from mpt_extension_sdk.pipeline import BasePipeline, BaseStep


class PurchasePipeline(BasePipeline):
    """Purchase pipeline."""

    @override
    @property
    def steps(self) -> list[BaseStep]:
        return [
            DemoStep(),
        ]
