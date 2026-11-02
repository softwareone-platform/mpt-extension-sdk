# Webhook Routes

Use `WebhookRouter` when the platform must get an immediate answer from the
extension, for example to validate a draft order while the user is in the order
wizard. The Extensions Service registers each webhook from the extension
metadata, so the declaration is all the platform needs.

## Declaring a webhook

Use `webhook(...)` to register a webhook handler. The route name is the handler
function name.

```python
from mpt_extension_sdk import WebhookRouter
from mpt_extension_sdk.webhooks import OrderWebhookContext, WebhookResponse, WebhookType

webhook_router = WebhookRouter(prefix="/webhooks")


@webhook_router.webhook(
    "/orders/validate",
    type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
    description="Validate purchase orders in Draft status",
    criteria={"product.id": "PRD-5516-5707"},
)
async def validate_purchase_order_draft(ctx: OrderWebhookContext) -> WebhookResponse:
    order = ctx.order.without_errors()
    account_type = order.parameters.get_ordering_value("accountType")
    if isinstance(account_type, str) and account_type in {"NewAccount", "ExistingAccount"}:
        return WebhookResponse.ok(order)

    return WebhookResponse.ok(
        order.with_ordering_error(
            "accountType",
            {"id": "MOCK001", "message": f"Invalid account type: {account_type}"},
        )
    )
```

- `path`: the route path, joined to the router prefix.
- `type`: a `WebhookType` member or a plain string. A string is matched against
  the known types case-insensitively; a type the SDK does not know is kept as the
  given string and logged as a warning, so a type the platform adds later can be
  used before the SDK lists it.
- `description`: the webhook description published in the metadata.
- `criteria`: one mapping, or a list of mappings to request one platform webhook
  per mapping on the same route, for example one per product. Keys and values
  must be non-empty strings.
- `context_adapter_type`: adapts the webhook context to a custom context, as in
  `EventRouter` (see
  [contexts-and-pipelines.md](contexts-and-pipelines.md#adapt-the-execution-context)).
  The adapter must inherit from the context the webhook type receives, for
  example `OrderWebhookContext`. `WebhookRouter(context_adapter_type=...)` sets
  the default of every route of the router.

The mock app's `validate_purchase_order_draft`
([`mock_app/api/routes/webhook.py`](../../mock_app/api/routes/webhook.py)) is a
working example. The `webhook /` requests of the Postman collection
([`mock_app/docs/postman_collection.json`](../../mock_app/docs/postman_collection.json))
call it with an invalid account type and then with the value fixed.

`WebhookType.object_type` returns the platform object the webhook carries
(`WebhookObjectType.ORDER`, `ACCOUNT` or `REQUEST`).

## Registration rules

The SDK rejects a declaration with a `ValueError` when it is registered:

- the type or the description is empty;
- `criteria` is empty, contains an empty mapping, or repeats a mapping;
- another webhook route already declares the same type with the same criteria.

It also rejects, with a `TypeError`, a context adapter that does not inherit
from the context of the webhook type, for example an adapter of
`OrderWebhookContext` on a `validateAccount` route. A webhook type the SDK does
not know receives `WebhookContext`, so its adapter cannot inherit from a typed
context such as `AccountWebhookContext`. The check covers the adapter set on the
route and the default of the router.

## Webhook context

The handler, sync or async, receives a context typed by the object the webhook
carries:

| Webhook type | Context |
| --- | --- |
| Order validation types and `selectOrderLines` | `OrderWebhookContext` with `ctx.order` (`OrderSimple`) |
| `validateAccount` | `AccountWebhookContext` with `ctx.account` |
| `validateRequest` | `RequestWebhookContext` with `ctx.mpt_request` |
| Unknown type | `WebhookContext` |

Every webhook context also exposes the `BaseContext` fields, `ctx.payload` (the
webhook body) and `ctx.request` (the HTTP request, as in API routes).

Fields the platform adds to a payload do not break the context: the models keep
them, and `WebhookResponse` returns them as they arrived. A payload without a
required field of the model, such as the order `id` or `product`, is answered
with `EXT003`.

The platform sends the order with the errors of the previous answer. Clear them
with `ctx.order.without_errors()` before validating again, as the example does:
it sets the order error and every ordering parameter error to `None`, so the
answer clears them.

To report a problem, return the order with the error set:
`order.with_ordering_error(external_id, error)` puts it on an ordering
parameter, and `order.with_error(error)` on the order itself. Both return a copy,
so they can be chained after `without_errors()`:

```python
order = (
    ctx.order
    .without_errors()
    .with_ordering_error("accountType", {"id": "MOCK001", "message": "Invalid account type"})
    .with_error({"id": "MOCK002", "message": "The order cannot be placed"})
)
```

## Responses and errors

| Handler outcome | HTTP response |
| --- | --- |
| Returns `WebhookResponse.ok(payload)` | `200` with the payload, without a `data` envelope |
| Returns `WebhookResponse.error(error_id, message)` | `500`, or the given `status_code`, with `{"id": error_id, "message": message}` |
| Raises `WebhookError(error_id, message)` | `500`, or the `status_code` of the error, with `{"id": error_id, "message": message}` |
| Any other exception, or a return value that is not a `WebhookResponse` | `500` with `{"id": "EXT001", ...}` and the correlation id |
| Missing or invalid token, or a token for another extension | `401` with `{"id": "EXT002", ...}` |
| Body that is not a JSON object, or does not match the context model | `400` with `{"id": "EXT003", ...}` |

`WebhookResponse.ok` leaves out model fields that were not set, so a model
goes back with the shape it arrived with.

The platform treats every answer that is not `200` as a failed call. Report
business validation problems in the returned object, and keep errors for calls
the extension cannot answer.

Webhook calls are synchronous: there is no Task and no retry, and the platform
stops waiting after its timeout. Keep handlers fast and move long work to an
event handler or an API route.

## Metadata

Each criteria set publishes one `webhooks` entry in `meta.yaml`, all with the
route path. See [cli.md](cli.md#metadata-metayaml).
