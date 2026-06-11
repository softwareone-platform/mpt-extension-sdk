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

## Installations

Use `ctx.mpt_api_service.installations` to look up extension installations
through the integration installations endpoint. To check whether an extension
is already installed in a given account before deciding to invite it:

```python
already_installed = await ctx.mpt_api_service.installations.exists_for_account(
    extension_id="EXT-1234",
    account_id="ACC-5678",
)
```

`exists_for_account` returns ``True`` whenever the API returns at least one
matching installation regardless of installation status (`Invited`,
`Installed`, `Expired`, `Uninstalled`). It returns ``False`` only for an empty
result set. Other API errors are propagated unchanged.
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
