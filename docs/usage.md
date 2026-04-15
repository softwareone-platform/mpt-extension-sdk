# SDK Usage

This guide shows how to build on top of `mpt-extension-sdk`.

## Install The SDK

Install the package in a consumer project:

```bash
pip install mpt-extension-sdk
```

```bash
uv add mpt-extension-sdk
```

## Create An Extension App

Start with `ExtensionApp` and `ExtensionRouter`. The extension app is the root
SDK object for one extension package. Routers group related event handlers and
expose metadata consumed by the runtime.

```python
# app.py
from mpt_extension_sdk.extension_app import ExtensionApp

from mock_app.api.routes import orders_router

ext_app = ExtensionApp(prefix="/api/v1")
ext_app.include_router(orders_router)
```

```python
# api/routes.py
from mpt_extension_sdk.extension_app import ExtensionRouter

orders_router = ExtensionRouter(prefix="/events/orders")


@orders_router.route(
    path="/purchase", name="orders-purchase", event="platform.commerce.order.status_changed"
)
async def process_order(event, context):
    """Process order events."""
```

Keep `app.py` imports deterministic. The runtime imports the exported
`ext_app` during metadata generation, so avoid network calls, filesystem I/O,
or other heavy side effects at module import time.

## Register Handlers

Use `route(...)` when the platform event is non-task-based.

```python
from mpt_extension_sdk.extension_app import ExtensionRouter

orders_router = ExtensionRouter(prefix="/events/orders")


@orders_router.route(path="/change", name="orders-change", event="platform.commerce.order.created")
async def process_order_change(event, context):
    """Process a task-backed order event."""
```


Use `task_route(...)` when the platform event is task-backed and the runtime
must manage task lifecycle operations.

```python
from mpt_extension_sdk.extension_app import ExtensionRouter

orders_router = ExtensionRouter(prefix="/events/orders")


@orders_router.task_route(
    path="/change", name="orders-change", event="platform.commerce.order.created"
)
async def process_order_change(event, context):
    """Process a task-backed order event."""
```

## Build A Processing Pipeline

Use `BasePipeline`, `BaseStep`, and execution contexts for multi-step
processing flows.

```python
from typing import Self, override

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

## Adapt The Execution Context

Use `ContextAdapter` when an extension needs a custom context type built from
the SDK-provided base context.

```python
from dataclasses import dataclass, field
from typing import Self

from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.pipeline import ContextAdapter, OrderContext


@dataclass(kw_only=True)
class CustomOrderContext(OrderContext, ContextAdapter):
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_context(cls, ctx: OrderContext) -> Self:
        return cls(**ctx.__dict__)


ext_app = ExtensionApp(order_context_type=CustomOrderContext)
```

## Run An Extension

Use the `mpt-ext` CLI command when running an extension built on top of the SDK:

```bash
mpt-ext run --local
mpt-ext run
mpt-ext meta generate
mpt-ext meta validate
```

- `mpt-ext run --local` starts the FastAPI + uvicorn runtime for local development.
- `mpt-ext run` generates `meta.yaml`, registers the extension instance, and starts
  the platform runtime with mrok/ziticorn.
- `mpt-ext meta generate` writes the metadata artifact derived from the exported
  `ext_app`.
- `mpt-ext meta validate` checks that the checked-in `meta.yaml` matches the generated
  metadata.

## Configure The Runtime

The SDK commonly relies on:

- `SDK_EXTENSION_URL`
- `SDK_EXTENSION_API_KEY`
- `SDK_EXTENSION_ID`
- `MPT_API_BASE_URL`
- `MPT_API_TOKEN`

Example configuration:

```dotenv
SDK_EXTENSION_URL=https://extensions.example.com
SDK_EXTENSION_API_KEY=<extension-api-key>
SDK_EXTENSION_ID=EXT-1234
MPT_API_BASE_URL=https://api.s1.show
MPT_API_TOKEN=<marketplace-api-token>
SDK_LOCAL_PORT=8080
```

See [configuration.md](configuration.md) for the runtime environment-variable reference.

## Use Marketplace Services

Execution contexts expose `ctx.mpt_api_service` as the main SDK entry point for
Marketplace reads and writes.

- service `get_*` methods return typed SDK models
- `create(...)` methods accept a complete resource object, either as a plain mapping
  or as an SDK model with `to_dict()`
- `update(..., attributes)` accepts a partial attribute mapping for flexible updates
- order transitions such as `complete(...)`, `query(...)`, and `fail(...)` remain
  explicit service methods instead of generic updates

Example:

```python
from mpt_extension_sdk.pipeline import BaseStep, OrderContext


class UpdateOrderStep(BaseStep):
    async def process(self, ctx: OrderContext) -> None:
        await ctx.mpt_api_service.orders.update(
            ctx.order_id,
            attributes={
                "parameters": ctx.order.parameters.to_dict(),
            },
        )

        await ctx.mpt_api_service.orders.complete(
            ctx.order_id,
            template={"id": "TPL-1", "name": "Completed"},
            attributes={
                "parameters": ctx.order.parameters.to_dict(),
                "externalIds": ctx.order.external_ids.to_dict(),
            },
        )
```

This keeps partial updates flexible for extension-specific fields while still
making status transitions explicit in the SDK API.

## What The SDK Provides

- `ExtensionApp` and `ExtensionRouter` for extension registration and route metadata
- FastAPI + uvicorn runtime wiring for task and non-task Marketplace events
- typed execution contexts, context adapters, and pipeline primitives
- Marketplace service helpers, runtime settings discovery, and observability hooks
