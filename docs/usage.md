# SDK Usage

This guide shows how to build an extension package on top of `mpt-extension-sdk`.

## Install The SDK

Install the package in a consumer project:

```bash
pip install mpt-extension-sdk
```

```bash
uv add mpt-extension-sdk
```

## Extension Package Shape

The runtime auto-discovers exactly one top-level package in the working directory. That package
must export:

- `app.py` with `ext_app`
- `settings.py` with `ExtensionSettings`

`ExtensionSettings` must inherit from
`mpt_extension_sdk.settings.extension.BaseExtensionSettings`.

Keep imports in `app.py` deterministic. The runtime imports `ext_app` to build
metadata before startup, so avoid network calls, filesystem I/O, or other heavy
side effects at module import time.

## Create An Extension App

Start with `ExtensionApp` and the router family that matches your use case. The
extension app is the root SDK object for one extension package.

```python
# mock_app/app.py
from mpt_extension_sdk import ExtensionApp

from mock_app.api.routes import orders_router

ext_app = ExtensionApp(prefix="/api/v2")
ext_app.include_router(orders_router)
```

```python
# mock_app/api/routes.py
from mpt_extension_sdk.routing import EventRouter

orders_router = EventRouter(prefix="/events/orders")
```

The SDK also exposes `ApiRouter`, `ScheduleRouter`, and `PlugRouter`. In the
current SDK version, only `EventRouter` is implemented end-to-end in runtime
and metadata generation.

## Register Event Handlers

Use `event(...)` for non-task events:

```python
from mpt_extension_sdk import EventRouter

orders_router = EventRouter(prefix="/events/orders")


@orders_router.event(
    path="/purchase",
    name="orders-purchase",
    event="platform.commerce.order.purchased",
)
async def process_purchase(event, context):
    """Process a non-task order or agreement event."""
```

Use `task(...)` for task-backed events. The runtime starts, completes,
fails, or reschedules the Marketplace task around the handler execution.

```python
from mpt_extension_sdk import EventRouter

orders_router = EventRouter(prefix="/events/orders")


@orders_router.task(
    path="/change",
    name="orders-change",
    event="platform.commerce.order.created",
)
async def process_order_change(event, context):
    """Process a task-backed event."""
```

Within one router or app, each route `name` and `path` must be unique. Event
subscriptions must also be unique among event routes.

## Event Context Resolution

The runtime builds the handler context from `event.object.object_type` in the
received payload:

- `Order` -> `OrderContext`
- `Agreement` -> `AgreementContext`

This means a single extension app can register routes that receive either
orders or agreements, and the SDK resolves the correct context family for each
request at runtime.

## Adapt The Execution Context

Use a context adapter when an extension needs to enrich the SDK-provided
context with extension-specific fields or dependencies. The adapter must return
the same context family it receives at runtime.

```python
from dataclasses import dataclass, field
from typing import Self

from mpt_extension_sdk import EventRouter
from mpt_extension_sdk.pipeline import OrderContext
from mpt_extension_sdk.context import ContextAdapter


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

## Run An Extension

Use the `mpt-ext` CLI command when running an extension built on top of the SDK:

```bash
mpt-ext run --local
mpt-ext run
mpt-ext meta generate
mpt-ext meta validate
```

- `mpt-ext run --local` starts the local `FastAPI + uvicorn` runtime.
- `mpt-ext run` writes `meta.yaml`, registers the extension instance, and starts
  the platform runtime with `mrok`/`ziticorn`.
- `mpt-ext meta generate` writes metadata derived from `ext_app.to_meta_config()`.
- `mpt-ext meta validate` compares the checked-in `meta.yaml` with generated
  metadata and writes `meta.generated.yaml` when they differ.

## Configure The Runtime

The SDK commonly relies on:

- `SDK_EXTENSION_URL`
- `SDK_EXTENSION_API_KEY`
- `SDK_EXTENSION_ID`
- `MPT_API_BASE_URL`

Example configuration:

```dotenv
SDK_EXTENSION_URL=https://extensions.example.com
SDK_EXTENSION_API_KEY=<extension-api-key>
SDK_EXTENSION_ID=EXT-1234
MPT_API_BASE_URL=https://api.s1.show
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

Event handler contexts use the JWT delivered in the event request
`Authorization` header. Authenticated API route contexts use the request auth
context to generate an account-scoped Marketplace token. The auth context is
also carried on SDK execution contexts as `ctx.auth`.

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

## What The SDK Provides

- `ExtensionApp` and router-family classes for route registration and metadata
- task and non-task event runtime wiring
- typed execution contexts, context adapters, and pipeline primitives
- Marketplace service helpers, settings discovery, and observability hooks
