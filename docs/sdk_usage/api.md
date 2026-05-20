# Authenticated API Routes

Use `APIRouter` when the extension must expose authenticated HTTP endpoints to
the platform or other authorized consumers. The incoming request must include an
`Authorization` bearer token for the configured extension.

```python
from mpt_extension_sdk import APIRouter
from mpt_extension_sdk.api import APIResponse

orders_api = APIRouter(prefix="/orders")


@orders_api.get(path="/{order_id}", name="orders-detail")
async def get_order(order_id: str, ctx):
    order = await ctx.mpt_api_service.orders.get_by_id(order_id)
    return APIResponse.ok(payload=order.to_dict())
```

Include the router in the extension app the same way as any other route family:

```python
from mpt_extension_sdk import ExtensionApp

from mock_app.api.routes.api import api_router
from mock_app.api.routes.event import orders_router

ext_app = ExtensionApp(prefix="/api/v2")
ext_app.include_router(api_router)
ext_app.include_router(orders_router)
```

`APIRouter` exposes one method per HTTP operation: `get`, `post`, `put`,
`patch`, and `delete`. Each route defines `path`, `name`, and an optional
`body_validator`. Route names must remain unique within the app. API routes are
also unique by `(method, path)`, so `GET /agreements` and `POST /agreements`
can coexist, but two `POST /agreements` registrations cannot.

## Context

API handlers receive a request-scoped context parameter, usually named `ctx`.
The SDK extracts trusted claims from the validated JWT and exposes them through
`ctx.auth`:

- `ctx.auth.account.id`
- `ctx.auth.account.type`
- `ctx.auth.extension_id`
- `ctx.auth.permissions`

The same context exposes request metadata through `ctx.request`:

- `ctx.request.query`
- `ctx.request.headers`
- `ctx.request.method`
- `ctx.request.url`
- `ctx.request.body`
- `ctx.request.pagination`

For API routes, `ctx.mpt_api_service` is built with an account-scoped token
derived from the authenticated account. The SDK caches and refreshes that token
automatically when it expires.

```python
from mpt_extension_sdk.api import APIContext, APIResponse, ForbiddenError


@orders_api.post(path="/{order_id}/sync", name="orders-sync")
async def sync_order(order_id: str, ctx: APIContext) -> APIResponse:
    if not ctx.auth.account.is_client():
        raise ForbiddenError("Only client accounts are supported")

    await OrderSync().execute(order_id=order_id, account_id=ctx.auth.account.id)
    return APIResponse.no_content()
```

## Query Parameters

Query parameters are available through typed helpers:

```python
@orders_api.get(path="", name="orders-list")
async def list_orders(ctx: APIContext) -> APIResponse:
    include_closed = ctx.request.query.get_bool("include_closed", default=False)
    limit = ctx.request.query.get_int("limit", default=100)
    tags = ctx.request.query.get_list("tag")
    orders = await OrderService().list_orders(
        include_closed=include_closed,
        limit=limit,
        tags=tags,
    )
    return APIResponse.ok(payload=orders)
```

Boolean query parsing accepts `true`/`false`, `1`/`0`, and `yes`/`no`
case-insensitively. Unrecognized boolean values return the provided default.
Integer query parsing returns `422 Unprocessable Content` when the value cannot
be parsed as an integer.

## Request Bodies

For request bodies, pass a `BaseSchema` validator. The SDK validates the
request before invoking the handler and injects the validated object as a
handler argument.

```python
from pydantic import Field

from mpt_extension_sdk import APIRouter
from mpt_extension_sdk.api import APIContext, APIResponse
from mpt_extension_sdk.schemas import BaseSchema


class SyncAgreementPayload(BaseSchema):
    status: str = Field(pattern="^(Processing|Complete)$")


agreements_api = APIRouter(prefix="/agreements")


@agreements_api.post(
    path="/{agreement_id}/sync",
    name="agreements-sync",
    body_validator=SyncAgreementPayload,
)
async def sync_agreement(
    agreement_id: str,
    payload: SyncAgreementPayload,
    ctx: APIContext,
) -> APIResponse:
    return APIResponse.accepted(payload={"id": agreement_id, "status": payload.status})
```

If body validation fails, the SDK returns `422 Unprocessable Content` using the
problem-details error format. Invalid JSON payloads also return `422`.

## Responses

Authenticated API handlers must return `APIResponse`. For responses with a
body, the SDK serializes the result using the standard JSON envelope:

```json
{
  "data": {},
  "meta": {},
  "links": {}
}
```

Use the response helper that matches the endpoint semantics:

- `APIResponse.ok(payload=...)`
- `APIResponse.created(payload=...)`
- `APIResponse.accepted(payload=...)`
- `APIResponse.paginated(PaginatedResult.from_pagination(...))`
- `APIResponse.no_content()`

For page-based collection responses, use `ctx.request.pagination` and
`PaginatedResult`. The SDK parses `page` and `page_size` lazily from the query
string and builds `meta` plus pagination links from the current request URL.

```python
from mpt_extension_sdk.api import APIContext, APIResponse, PaginatedResult


@orders_api.get(path="", name="orders-list")
async def list_orders(ctx: APIContext) -> APIResponse:
    pagination = ctx.request.pagination
    result = await OrderService().list_orders(
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

Raise `APIError` subclasses such as `ForbiddenError` or `NotFoundError` when
the handler must return a specific client-facing error. Unhandled exceptions
are treated as internal errors and returned as `500 Internal Server Error`
problem-details responses with the current correlation identifier.
