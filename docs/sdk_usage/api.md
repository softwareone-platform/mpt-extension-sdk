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
`body_validator`, plus the keyword-only `deferrable` and `timeouts` described in
[Deferrable Endpoints](#deferrable-endpoints). Route names must remain unique within the app. API routes are
also unique by `(method, path)`, so `GET /agreements` and `POST /agreements`
can coexist, but two `POST /agreements` registrations cannot. Paths that differ
only in a trailing slash or in a path parameter name count as the same path.

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
problem-details error format. Invalid JSON payloads, including bodies that cannot
be decoded, also return `422`.

## Responses

Authenticated API handlers must return `APIResponse`. For responses with a
body, the SDK serializes the result using the standard JSON envelope:

```json
{
  "data": {},
  "$meta": {}
}
```

Use the response helper that matches the endpoint semantics:

- `APIResponse.ok(payload=...)`
- `APIResponse.created(payload=...)`
- `APIResponse.accepted(payload=...)`
- `APIResponse.paginated(PaginatedResult.from_pagination(...))`
- `APIResponse.no_content()`

For offset-based collection responses, use `ctx.request.pagination` and
`PaginatedResult`. The SDK parses `offset` and `limit` lazily from the query
string and serializes pagination under `$meta.pagination`. Missing values
default to `offset=0` and `limit=100`. Both `offset` and `limit` must be
greater than or equal to `0`; `limit=0` is treated as a count-only request.

Paginated responses use this shape:

```json
{
  "$meta": {
    "pagination": {
      "offset": 0,
      "limit": 100,
      "total": 250
    }
  },
  "data": []
}
```

```python
from mpt_extension_sdk.api import APIContext, APIResponse, PaginatedResult


@orders_api.get(path="", name="orders-list")
async def list_orders(ctx: APIContext) -> APIResponse:
    pagination = ctx.request.pagination
    result = await OrderService().list_orders(
        offset=pagination.offset,
        limit=pagination.limit,
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

## Deferrable Endpoints

A deferrable endpoint also accepts a deferred call: the caller does not wait for
the handler, and follows the work as a platform Task instead. Declare it with
`deferrable=True` on any `APIRouter` method:

```python
from mpt_extension_sdk import APIRouter
from mpt_extension_sdk.api import APIContext, APIResponse

agreements_api = APIRouter(prefix="/agreements")


@agreements_api.post(path="/sync", name="agreements-sync", deferrable=True)
async def sync_agreements(ctx: APIContext) -> APIResponse | None:
    if ctx.task is None:
        synced = await synchronize(ctx)
        return APIResponse.ok(payload=synced.to_dict())

    await synchronize_with_progress(ctx)
    return None
```

The SDK publishes every deferrable endpoint in the `deferrables` block of
`meta.yaml` (see [cli.md](cli.md#metadata-metayaml)). The platform accepts a
deferred call only for an endpoint listed there.

### How a call is deferred

1. The caller adds the `MPT-Async: true` header to an ordinary call.
2. The Extension Service creates a Task and answers the caller itself with
   `202 Accepted` and the `MPT-Task-Id` header. The extension is not called yet.
3. The Extension Service then delivers the same request to the extension, with
   the same path, query, and body, without `MPT-Async` and with `MPT-Task-Id`.
4. The SDK starts the Task, runs the handler in the background, and completes,
   reschedules, or fails the Task from its outcome.

A call without `MPT-Async: true` reaches the handler as a regular request. A
call with it to an endpoint that is not deferrable is rejected by the Extension
Service with `409 Conflict`. Deferred calls are not deduplicated: two calls
create two Tasks and two executions, so handlers must be idempotent.

### Both call modes

A deferrable endpoint serves both modes with one handler, and the developer
implements both branches. `ctx.task` tells them apart:

| `ctx.task` | Mode | The handler returns |
| --- | --- | --- |
| `None` | Direct call | An `APIResponse`, sent to the caller |
| A `TaskHandle` | Deferred delivery | `None` or a `TaskResult`; the caller already got `202` |

`ctx.task.progress(...)` and `ctx.task.log(...)` report to the Task, as for
schedules (see [schedules.md](schedules.md#reporting-to-the-task)). They are
best-effort and only exist in the deferred branch.

The outcome of the deferred branch drives the Task, as for schedules (see
[schedules.md](schedules.md#handler-outcomes)): a return completes it,
`DeferError` reschedules it and the handler runs again from the beginning on
the next delivery, and `CancelError`, `FailError`, or any other exception fails
it. In the direct branch these errors are not API errors, so the caller gets a
`500`; raise `APIError` subclasses there instead.

### Task result

The Task `result` is an optional relative URI. Return `None` when the Task status
is the whole outcome. To point the caller at a resource, return a reference:

```python
from mpt_extension_sdk.api import TaskResult

return TaskResult.reference(f"/public/v1/commerce/agreements/{agreement_id}")
```

The SDK stores the URI on the Task before completing it, and the caller reads
the resource through `GET /public/v1/system/tasks/{id}/result`.
`TaskResult.reference` rejects a URI that does not start with `/`.

### Task timeouts

A deferrable endpoint can declare its own Task lifetime limits, in seconds:

```python
from mpt_extension_sdk import TaskTimeouts


@agreements_api.post(
    path="/sync",
    name="agreements-sync",
    deferrable=True,
    timeouts=TaskTimeouts(max_task_processing=3600, max_task_lifespan=7200),
)
async def sync_agreements(ctx: APIContext) -> APIResponse | None: ...
```

`TaskTimeouts` needs at least one of the two limits. A limit left out is not
published, so the platform default applies. The SDK reads its execution
deadline from the limits the Task publishes, as described in
[schedules.md](schedules.md#time-limits), and fails the Task with a processing
timeout reason when the handler exceeds it.

### Registration rules

The SDK rejects a wrong declaration when the route is registered, so the
mistake surfaces when the extension starts:

- the handler must be a coroutine function (`async def`), because the deferred
  branch runs under the task runner, which only accepts an awaitable;
- the path cannot declare path parameters, because the platform does not
  resolve them for a deferred call. Take the input from the request body, and
  keep it small: the platform limits a deferred request body to 4 KB;
- `timeouts` is only accepted together with `deferrable=True`.
