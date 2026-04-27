from typing import Self, override

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.pipeline import EventBaseContext, OrderContext


class MockContext(OrderContext, ContextAdapter):
    """Mock context as example."""

    @property
    def mock_field(self) -> str:
        """Mock field as example."""
        return "mock_field"

    @override
    @classmethod
    def from_context(cls, ctx: EventBaseContext) -> Self:
        return cls(**ctx.__dict__)
