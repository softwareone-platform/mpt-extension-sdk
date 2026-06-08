# Marketplace Services

SDK handler contexts expose `ctx.mpt_api_service` as the main entry point for
Marketplace reads and writes. The same service is available from event handlers,
task-backed handlers, authenticated API handlers, context adapters, and pipeline
steps that receive an SDK context.

- service `get_*` methods return typed SDK models
- `create(...)` methods accept a complete resource object, either as a plain mapping
  or as an SDK model with `to_dict()`
- `update(..., attributes)` accepts a partial attribute mapping for flexible updates
- order transitions such as `complete(...)`, `query(...)`, and `fail(...)` remain
  explicit service methods instead of generic updates

The SDK builds the service from the request context:

- event and task routes use the JWT delivered in the event request
  `Authorization` header
- authenticated API routes use `ctx.auth.account` to obtain an account-scoped
  Marketplace token
- the auth context is also carried as `ctx.auth` when the request provides one

When a handler needs to call the MPT API as a different account than the
caller (for example as the Operations account when reacting to a Client
agreement event), build the service from the account id directly:

```python
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService

mpt_api_service = await MPTAPIService.from_account_id(base_url, account_id)
```

`from_account_id` reuses the same account-scoped token mechanism as
`from_auth_context` and resolves the extension identity from runtime settings,
so the resulting service refreshes its token per request like any other
account-scoped service.

## Operations-Authenticated Service Per Handler

For the common case of acting as the Operations account from a Client-account
event handler, the SDK provides the `with_operations_mpt_api_service` decorator.
It reads the Operations account id from extension settings, builds the
account-scoped service, and exposes it as `ctx.ops_mpt_api_service`.
`ctx.mpt_api_service` keeps the caller-account scope unchanged.

```python
from mpt_extension_sdk.decorators import with_operations_mpt_api_service


@orders_router.task(
    path="/change",
    name="orders-change",
    event="platform.commerce.order.changed",
)
@with_operations_mpt_api_service()
async def process_order_change(event: TaskEvent, ctx: OrderContext):
    # ctx.mpt_api_service is still scoped to the caller account
    # ctx.ops_mpt_api_service is scoped to the Operations account
    await ctx.ops_mpt_api_service.orders.get_by_id(ctx.order_id)
```

The decorator reads `ctx.ext_settings.mpt_ops_account_id` by default. Override
the source attribute with `@with_operations_mpt_api_service(settings_attr=...)`
when the extension exposes the account id under a different field. To use a
custom `MPTAPIService` subclass, pass `service_type=...`.

## API Handler Example

```python
from mpt_extension_sdk.api import APIContext, APIResponse


async def list_agreements(ctx: APIContext) -> APIResponse:
    agreements = await ctx.mpt_api_service.agreements.get_all(batch_size=50)
    return APIResponse.ok(payload=agreements)
```

## Pipeline Example

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
