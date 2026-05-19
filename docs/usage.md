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

The SDK also exposes `APIRouter`, `ScheduleRouter`, and `PlugRouter`.
`EventRouter` and `APIRouter` are mounted by the runtime. `PlugRouter` is
declarative: its plug definitions are emitted into metadata and its static
assets are exposed through `/static`. `ScheduleRouter` is modeled in the SDK
contract but is not yet mounted by the runtime or emitted into metadata.

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

## Register Authenticated API Handlers

Use `APIRouter` for authenticated extension API endpoints. The incoming request
must include an `Authorization` bearer token for the configured extension.

```python
from mpt_extension_sdk import APIRouter
from mpt_extension_sdk.api import APIResponse

orders_api = APIRouter(prefix="/orders")


@orders_api.get(path="/{order_id}", name="orders-detail")
async def get_order(order_id: str, ctx):
    order = await ctx.mpt_api_service.orders.get_by_id(order_id)
    return APIResponse.ok(payload=order.to_dict())
```

For request bodies, pass a `BaseSchema` validator. The validated model is passed
to the handler through the body parameter.

```python
from mpt_extension_sdk import APIRouter
from mpt_extension_sdk.api import APIResponse
from mpt_extension_sdk.schemas import BaseSchema


class SyncAgreementPayload(BaseSchema):
    status: str


agreements_api = APIRouter(prefix="/agreements")


@agreements_api.post(
    path="/{agreement_id}/sync",
    name="agreements-sync",
    body_validator=SyncAgreementPayload,
)
async def sync_agreement(agreement_id: str, payload: SyncAgreementPayload, ctx):
    return APIResponse.accepted(payload={"id": agreement_id, "status": payload.status})
```

## Register UI Plugs

Use `PlugRouter` to declare widgets that MPT can register during extension
instance registration. Plug definitions are metadata only; the SDK does not
build or render frontend assets.

```python
from mpt_extension_sdk import ExtensionApp, Plug, PlugRouter

plug_router = PlugRouter()


@plug_router.register()
def register_plugs() -> list[Plug]:
    return [
        Plug(
            id="adobe",
            name="Adobe",
            description="Adobe widget",
            icon="adobe.png",
            socket="commerce.agreements.agreement",
            condition="eq(product.id,'PRD-1234-5677')",
            href="main-menu.js",
        )
    ]


ext_app = ExtensionApp(prefix="/")
ext_app.include_router(plug_router)
```

The `PlugRouter` instance named `plug_router` owns the `register_plugs`
provider until `ExtensionApp.include_router` attaches it to the extension app.

`href` and `icon` should be filenames or paths relative to the local `static/`
folder, such as `main-menu.js` or `images/icon.png`. The SDK normalizes them
under `/static/` in generated metadata, so `href="main-menu.js"` becomes
`/static/main-menu.js` and `icon="images/icon.png"` becomes
`/static/images/icon.png`. The `mpt-ext meta validate` command checks that every
referenced file exists locally.

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
  metadata, validates plug static assets, and writes `meta.generated.yaml` when
  validation fails.

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
