# Webhook Routes

Use `WebhookRouter` to declare the platform webhooks an extension answers. The
Extensions Service registers each webhook from the extension metadata, so the
declaration is all the platform needs.

The runtime does not serve webhook routes yet: an extension app that includes a
`WebhookRouter` publishes its webhooks in `meta.yaml`, but the runtime refuses to
mount them with a `ConfigError`.

## Declaring a webhook

Use `webhook(...)` to register a webhook handler. The route name is the handler
function name.

```python
from mpt_extension_sdk import WebhookRouter
from mpt_extension_sdk.webhooks import WebhookType

webhook_router = WebhookRouter(prefix="/webhooks")


@webhook_router.webhook(
    "/orders/validate",
    type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
    description="Validate purchase orders in Draft status",
    criteria={"product.id": "PRD-5516-5707"},
)
def validate_purchase_order_draft(ctx): ...
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

## Metadata

Each criteria set publishes one `webhooks` entry in `meta.yaml`, all with the
route path. See [cli.md](cli.md#metadata-metayaml).
