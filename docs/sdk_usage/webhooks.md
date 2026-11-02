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
from mpt_extension_sdk.webhooks import WebhookContext, WebhookResponse, WebhookType

webhook_router = WebhookRouter(prefix="/webhooks")


@webhook_router.webhook(
    "/orders/validate",
    type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
    description="Validate purchase orders in Draft status",
    criteria={"product.id": "PRD-5516-5707"},
)
def validate_purchase_order_draft(ctx: WebhookContext) -> WebhookResponse:
    return WebhookResponse.ok(ctx.payload)
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

`WebhookType.object_type` returns the platform object the webhook carries
(`WebhookObjectType.ORDER`, `ACCOUNT` or `REQUEST`).

## Registration rules

The SDK rejects a declaration with a `ValueError` when it is registered:

- the type or the description is empty;
- `criteria` is empty, contains an empty mapping, or repeats a mapping;
- another webhook route already declares the same type with the same criteria.

## Webhook context

The handler receives a `WebhookContext`, sync or async. It exposes the
`BaseContext` fields, `ctx.payload` (the webhook body) and `ctx.request` (the
HTTP request, as in API routes).

## Responses and errors

| Handler outcome | HTTP response |
| --- | --- |
| Returns `WebhookResponse.ok(payload)` | `200` with the payload, without a `data` envelope |
| Returns `WebhookResponse.error(error_id, message)` | `500`, or the given `status_code`, with `{"id": error_id, "message": message}` |
| Raises `WebhookError(error_id, message)` | `500`, or the `status_code` of the error, with `{"id": error_id, "message": message}` |
| Any other exception, or a return value that is not a `WebhookResponse` | `500` with `{"id": "EXT001", ...}` and the correlation id |
| Missing or invalid token, or a token for another extension | `401` with `{"id": "EXT002", ...}` |
| Body that is not a JSON object | `400` with `{"id": "EXT003", ...}` |

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
