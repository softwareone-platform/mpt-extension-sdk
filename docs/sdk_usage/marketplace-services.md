# Marketplace Services

SDK handler contexts expose `ctx.mpt_api_service` as the main entry point for
Marketplace reads and writes. The same service is available from event handlers,
task-backed handlers, authenticated API handlers, context adapters, and pipeline
steps that receive an SDK context.

Contexts also expose `ctx.vendor_mpt_api_service`, the same service authenticated
as the vendor account that owns the extension. See
[Two Account Identities](#two-account-identities) for when to use each.

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
- the authenticated context is always carried as `ctx.auth`

## Two Account Identities

Every context carries two services, each authenticated as a different account:

| Field | Authenticated as | Use it for |
| --- | --- | --- |
| `ctx.mpt_api_service` | the account in the incoming request token, available as `ctx.auth.account` | anything scoped to the caller: reading and writing the objects the request is about |
| `ctx.vendor_mpt_api_service` | the vendor account that owns the extension | operations that must act as the extension owner, regardless of who triggered the request |

Use `ctx.mpt_api_service` by default. Depending on where the extension is
installed, the calling account is a client or an operations account, so it is not
the extension owner. Reach for `ctx.vendor_mpt_api_service` only when a flow has
to act as the vendor that owns the extension.

The vendor account cannot be taken from the business object: `agreement.vendor`
and `authorization.vendor` identify the vendor of the product in that agreement,
which is not by definition the extension owner, and no such field exists for
schedule contexts.

Both fields expose the same `MPTAPIService` service methods:

```python
from mpt_extension_sdk.pipeline import ScheduleContext


async def sync_vendor_agreements(ctx: ScheduleContext) -> None:
    caller_agreements = await ctx.mpt_api_service.agreements.get_all(limit=50)
    vendor_agreements = await ctx.vendor_mpt_api_service.agreements.get_all(limit=50)
```

`mock_app/api/routes/api.py` carries a runnable version of this as the
`vendor-agreements-list` route.

The two services authenticate differently:

- `ctx.mpt_api_service` exchanges the extension API key for an
  installation-scoped token for the calling account, so it requires the
  extension to be installed in that account
- `ctx.vendor_mpt_api_service` uses the extension API key directly, which the
  platform always scopes to the vendor that owns the extension

That difference matters: the owner account does not install its own extension,
so the installation-scoped exchange does not apply to it. Neither service issues
an HTTP request while the context is built.

Extensions that subclass `MPTAPIService` and pass it as `mpt_api_service_type`
get their subclass in both fields.

`vendor_mpt_api_service` has no default, so code that builds a context directly
with keyword arguments — usually a test fixture — has to pass it. Contexts built
by the SDK routes, contexts mocked with `Mock(spec=...)`, and context adapters
that forward `ctx.__dict__` need no change.

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

To create a new installation, build the payload as an `Installation` model (or
a plain mapping) and call `create`:

```python
from mpt_extension_sdk.models import Installation, InstallationReference

installation = await ctx.mpt_api_service.installations.create(
    Installation(
        account=InstallationReference(id="ACC-5678"),
        extension=InstallationReference(id="EXT-1234"),
        modules=[InstallationReference(id="MOD-1"), InstallationReference(id="MOD-2")],
    )
)
```

`create` accepts either an `Installation` SDK model or a plain mapping that
matches the Marketplace installation schema, and returns the `Installation`
parsed from the API response.

## API Handler Example

```python
from mpt_extension_sdk.api import APIContext, APIResponse


async def list_agreements(ctx: APIContext) -> APIResponse:
    agreements = await ctx.mpt_api_service.agreements.get_all(limit=50)
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
