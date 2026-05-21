# Contexts And Pipelines

## Adapt The Execution Context

Use a context adapter when an extension needs to enrich the SDK-provided
context with extension-specific fields or dependencies. The adapter must return
the same context family it receives at runtime.

```python
from dataclasses import dataclass, field
from typing import Self

from mpt_extension_sdk import EventRouter
from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.pipeline import OrderContext


@dataclass(kw_only=True)
class CustomOrderContext(OrderContext, ContextAdapter):
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_context(cls, ctx: OrderContext) -> Self:
        return cls(**ctx.__dict__)


orders_router = EventRouter(prefix="/events/orders")


@orders_router.task(
    path="/change",
    name="orders-change",
    event="platform.commerce.order.changed",
    context_adapter_type=CustomOrderContext,
)
async def process_order_change(event, context):
    assert isinstance(context, CustomOrderContext)
```

You can also configure `context_adapter_type` once on the router and override
it per route when needed.

## Build A Processing Pipeline

Use `BasePipeline`, `BaseStep`, and typed execution contexts for multi-step
processing flows.

```python
from typing import override

from mpt_extension_sdk.pipeline import BasePipeline, BaseStep, OrderContext


class ValidateOrderStep(BaseStep):
    async def process(self, ctx: OrderContext) -> None:
        """Validate the order payload."""


class ProcessOrderStep(BaseStep):
    async def process(self, ctx: OrderContext) -> None:
        """Run the main order logic."""


class PurchasePipeline(BasePipeline):
    @property
    @override
    def steps(self) -> list[BaseStep]:
        return [ValidateOrderStep(), ProcessOrderStep()]
```

The SDK exports both `OrderContext` and `AgreementContext`, and the runtime
hydrates the right one from `event.object.object_type`.
