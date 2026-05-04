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

from mock_app.api.routes.events import orders_router

ext_app = ExtensionApp(prefix="/api/v2")
ext_app.include_router(orders_router)
```

```python
# mock_app/api/routes/events.py
from mpt_extension_sdk import EventRouter

orders_router = EventRouter(prefix="/events/orders")
```

The SDK also exposes `APIRouter`, `ScheduleRouter`, and `PlugRouter`. In the
current SDK version, `EventRouter` and `APIRouter` are implemented end-to-end
in runtime. `ScheduleRouter` and `PlugRouter` remain declarative SDK contracts
for future runtime work.

## Register API Handlers

Use `APIRouter` when the extension must expose authenticated HTTP endpoints to
the platform or other authorized consumers.

```python
# mock_app/api/routes/api.py
from mpt_extension_sdk import APIRouter

api_router = APIRouter(prefix="/")
```

Include the router in the extension app the same way as any other route family:

```python
# mock_app/app.py
from mpt_extension_sdk import ExtensionApp

from mock_app.api.routes.api import api_router
from mock_app.api.routes.events import orders_router

ext_app = ExtensionApp(prefix="/api/v2")
ext_app.include_router(orders_router)
ext_app.include_router(api_router)
```

`APIRouter` exposes one method per HTTP operation:

- `get(...)`
- `post(...)`
- `put(...)`
- `patch(...)`
- `delete(...)`

Each route defines:

- `path`
- `name`
- optional `body_validator`

Route names must remain unique within the app. API routes also remain unique by
`(method, path)`, so `GET /agreements` and `POST /agreements` can coexist, but
two `POST /agreements` registrations cannot.

### Access Authenticated Context

API handlers receive a request-scoped context parameter, usually named `ctx`.
The Extension Framework service validates the incoming JWT before forwarding
requests to the SDK runtime. The SDK extracts those trusted claims through
`ctx.auth` and injects request metadata through `ctx.request`.

```python
from mpt_extension_sdk.api import APIContext, APIResponse, ForbiddenError


@api_router.post(
    path="/agreements/{agreement_id}/sync",
    name="agreement-sync",
)
async def handle_agreement_sync(
    agreement_id: str,
    ctx: APIContext,
) -> APIResponse:
    if not ctx.auth.account.is_client():
        raise ForbiddenError("Only client accounts are supported")

    await AgreementSync().execute(agreement_id=agreement_id, account_id=ctx.auth.account.id)
    return APIResponse.no_content()
```

The API context includes:

- `ctx.auth.account.id`
- `ctx.auth.account.type`
- `ctx.auth.extension_id`
- `ctx.auth.permissions`
- `ctx.request.query`
- `ctx.request.headers`
- `ctx.request.method`
- `ctx.request.url`
- `ctx.request.body`
- `ctx.request.pagination`
- `ctx.mpt_api_service`

For API routes, `ctx.mpt_api_service` is built with an account-scoped token
derived from the authenticated account. The SDK caches and refreshes that token
automatically when it expires.

`ctx.request.query` wraps the incoming query string and exposes typed helpers:

- `ctx.request.query.get("name")`
- `ctx.request.query.get_int("limit", default=100)`
- `ctx.request.query.get_bool("include_closed", default=False)`

Boolean query parsing accepts `true`/`false`, `1`/`0`, and `yes`/`no`
case-insensitively. Unrecognized boolean values return the provided default.
Integer query parsing returns `422 Unprocessable Content` when the value cannot
be parsed as an integer.

`ctx.request.body` contains the parsed JSON payload or `None` when the request
has no body. Invalid JSON returns `422 Unprocessable Content`.

### Validate Request Bodies

Use `BaseSchema` to describe the expected JSON payload and pass it through the
route `body_validator`. The SDK validates the request before invoking the
handler and injects the validated object as a handler argument.

```python
from pydantic import Field

from mpt_extension_sdk.api import APIContext, APIResponse
from mpt_extension_sdk.schemas import BaseSchema


class AgreementSchema(BaseSchema):
    status: str = Field(pattern="^(Processing|Complete)$")


@api_router.post(
    path="/agreements/{agreement_id}",
    name="agreement-create",
    body_validator=AgreementSchema,
)
async def handle_agreement_create(
    agreement_id: str,
    agreement: AgreementSchema,
    ctx: APIContext,
) -> APIResponse:
    created_agreement = await AgreementCreate().execute(
        agreement_id=agreement_id,
        payload=agreement,
    )
    return APIResponse.created(payload=created_agreement)
```

If body validation fails, the SDK returns `422 Unprocessable Content` using the
problem-details error format.

### Return API Responses

Authenticated API handlers must return `APIResponse`. The SDK serializes the
response using the standard JSON envelope:

```json
{
  "data": {},
  "meta": {},
  "links": {}
}
```

Use the helpers that match the response semantics:

- `APIResponse.ok(payload=...)`
- `APIResponse.created(payload=...)`
- `APIResponse.accepted(payload=...)`
- `APIResponse.paginated(PaginatedResult.from_pagination(...))`
- `APIResponse.no_content()`

For collection responses, you can optionally provide typed `Meta` and `Links`
objects:

```python
from mpt_extension_sdk.api import APIContext, APIResponse, Links, Meta


@api_router.get(
    path="/adobe/orders",
    name="adobe-orders",
)
async def get_adobe_orders(ctx: APIContext) -> APIResponse:
    orders = await AdobeOrderService(ctx).list_orders()
    meta = Meta(total=100, page=1, page_size=20, total_pages=5)
    links = Links(
        self="https://extension.example.com/api/v2/adobe/orders?page=1&page_size=20",
        first="https://extension.example.com/api/v2/adobe/orders?page=1&page_size=20",
        next="https://extension.example.com/api/v2/adobe/orders?page=2&page_size=20",
        last="https://extension.example.com/api/v2/adobe/orders?page=5&page_size=20",
    )
    return APIResponse.ok(payload=orders, meta=meta, links=links)
```

For page-based collection responses, use `ctx.request.pagination` and
`PaginatedResult`. The SDK parses `page` and `page_size` lazily from the query
string and builds `meta` plus pagination links from the current request URL.

```python
from mpt_extension_sdk.api import APIContext, APIResponse, PaginatedResult


@api_router.get(
    path="/adobe/orders",
    name="adobe-orders",
)
async def get_adobe_orders(ctx: APIContext) -> APIResponse:
    pagination = ctx.request.pagination
    result = await AdobeOrderService(ctx).list_orders(
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return APIResponse.paginated(
        PaginatedResult.from_pagination(
            pagination,
            payload=result.orders,
            total=result.total,
        )
    )
```

Raise `APIError` subclasses such as `ForbiddenError` when the handler must
return a specific client-facing error. Unhandled exceptions are treated as
internal errors and are returned as `500 Internal Server Error` problem-details
responses with the current correlation identifier.

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

## What The SDK Provides

- `ExtensionApp` and router-family classes for route registration and metadata
- task and non-task event runtime wiring
- typed execution contexts, context adapters, and pipeline primitives
- Marketplace service helpers, settings discovery, and observability hooks
