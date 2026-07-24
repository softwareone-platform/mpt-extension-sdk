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

A derived context is the right place for extension-specific mutable state that
must be carried across several steps in one execution — for example third-party
objects cached during the flow, or helper properties that make the flow
clearer. This keeps a clear separation between the immutable MPT snapshot
(`ctx.order`), extension working state (derived attributes), and generic
temporary state (`ctx.state`).

## Build A Processing Pipeline

Use `BasePipeline`, `BaseStep`, and typed execution contexts for multi-step
processing flows. A handler chooses a pipeline, and the pipeline runs ordered
business steps. The whole flow is readable in one place while each step stays
focused on one unit of work.

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

## Step Lifecycle

Each step runs through three lifecycle methods:

- `pre(ctx)` — pre-processing hook (optional override).
- `process(ctx)` — the business work. This is the only required override.
- `post(ctx)` — post-processing hook (optional override).

`post()` runs after `process()` both on success and on failure, so it is the
place for cleanup or compensating actions. If both `process()` and `post()`
raise, the `post()` exception is raised and chained from the original
processing error.

```python
from typing import override

from mpt_extension_sdk.errors.step import SkipStepError
from mpt_extension_sdk.pipeline import BaseStep, OrderContext


class ValidateDuplicateLines(BaseStep):
    @override
    async def pre(self, ctx: OrderContext) -> None:
        if len(ctx.order.lines) <= 1:
            raise SkipStepError("Order doesn't include more than one line.")

    @override
    async def process(self, ctx: OrderContext) -> None:
        """Validate that the order has no duplicate lines."""
```

Steps read from `ctx.order` (or `ctx.agreement`) as an immutable input and must
not mutate it. See [immutable-snapshots.md](immutable-snapshots.md) for the
read/build/persist/refresh pattern.

## Flow Control

Steps express outcomes by raising typed step errors. The pipeline interprets
them and continues, stops, or defers the flow:

- `SkipStepError` — skip this step, continue the pipeline.
- `StopStepError` — stop the pipeline with cancel semantics.
- `DeferStepError` — stop the pipeline and defer for a later retry.

See [error-handling.md](error-handling.md) for the full hierarchy and how each
error maps to the event response.

## Pipeline Hooks

`BasePipeline` exposes hooks that react to each step's outcome, so shared
behavior (status transitions, notifications, cleanup, extra logging) lives in
one place instead of being duplicated in every step:

- `on_step_succeeded(step, ctx)`
- `on_step_skipped(step, ctx, error)`
- `on_step_deferred(step, ctx, error)`
- `on_step_stopped(step, ctx, error)`
- `on_step_failed(step, ctx, error)`

The defaults log the outcome. Override only the hooks relevant to your shared
behavior — a common pattern is to keep success simple and centralize handling
of stopped or failed outcomes. Call `super()` to preserve the default logging.

```python
from abc import ABC
from typing import override

from mpt_extension_sdk.errors.step import StopStepError
from mpt_extension_sdk.pipeline import BasePipeline, BaseStep, OrderContext


class OrderPipeline(BasePipeline, ABC):
    @override
    async def on_step_stopped(
        self, step: BaseStep, ctx: OrderContext, error: StopStepError
    ) -> None:
        await super().on_step_stopped(step, ctx, error)
        await self._handle_failure_action(ctx)

    @override
    async def on_step_failed(self, step: BaseStep, ctx: OrderContext, error: Exception) -> None:
        await super().on_step_failed(step, ctx, error)
        await self._handle_failure_action(ctx)

    async def _handle_failure_action(self, ctx: OrderContext) -> None: ...
```

## Declaring Status Transitions

When a step needs a Marketplace status transition, it should declare the intent
on `ctx.order_state` (or `ctx.agreement_state`) and let a pipeline hook apply
the shared side effect. This keeps steps focused on business intent while the
hook owns the actual transition.

`OrderStatusAction` is a frozen value object with:

- `target_status` — an `OrderStatusActionType` (`FAIL` or `QUERY`)
- `message`
- `status_notes` (optional mapping)
- `parameters` (optional mapping)

`ctx.order_state` carries the declared `action` and a `handled` flag so a hook
can apply the transition exactly once. (`AgreementStatusAction` and
`agreement_state` mirror this, with `FAIL` as the only transition type.)

`OrderStatusActionType` only lists the transitions a step may declare. To read
or compare the current order status, use `OrderStatus`
(`mpt_extension_sdk.models.OrderStatus`), the `StrEnum` of all Marketplace
order statuses (`Draft`, `Quoted`, `Processing`, `Querying`, `Completed`,
`Failed`, `Deleted`) that also types `Order.status`. A known status is parsed
into an `OrderStatus` member (case-insensitive); an unknown status is kept as a
plain string and raises an `UnknownOrderStatusWarning` instead of failing:

```python
from mpt_extension_sdk.models import OrderStatus

if ctx.order.status == OrderStatus.COMPLETED:
    ...
```

```python
from typing import override

from mpt_extension_sdk.errors.step import StopStepError
from mpt_extension_sdk.pipeline import (
    BaseStep,
    OrderContext,
    OrderStatusAction,
    OrderStatusActionType,
)


class ValidateDuplicateLines(BaseStep):
    @override
    async def process(self, ctx: OrderContext) -> None:
        duplicates = self._get_duplicates(ctx.order.lines)
        if duplicates:
            ctx.order_state.action = OrderStatusAction(
                target_status=OrderStatusActionType.FAIL,
                message="Duplicate items found",
                status_notes={"duplicates": ",".join(duplicates)},
            )
            raise StopStepError("Duplicate items found")
```

The matching pipeline hook reads `ctx.order_state.action`, applies the
transition through `ctx.mpt_api_service`, and sets `handled = True`:

```python
async def _handle_failure_action(self, ctx: OrderContext) -> None:
    if ctx.order_state.action is None or ctx.order_state.handled:
        return

    action = ctx.order_state.action
    if action.target_status == OrderStatusActionType.FAIL:
        await ctx.mpt_api_service.orders.fail(ctx.order_id, ...)
    else:
        await ctx.mpt_api_service.orders.query(ctx.order_id, ...)

    ctx.order_state.handled = True
```
