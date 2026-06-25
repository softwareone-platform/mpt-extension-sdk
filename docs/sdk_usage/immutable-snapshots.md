# Immutable MPT Snapshots

MPT models on the context (`ctx.order`, `ctx.agreement`, and their nested
objects) must be treated as immutable snapshots of the current Marketplace
state. Event-driven flows are retried, and hidden in-memory mutations make
retries and later steps hard to reason about.

The correct pattern is:

1. read from `ctx.order` or `ctx.agreement`
2. build a new payload explicitly
3. persist it through `ctx.mpt_api_service`
4. refresh only when later logic needs the updated representation

Do not mutate the snapshot in place:

```python
# Avoid - mutating the snapshot
ctx.order.parameters.set_fulfillment_value(...)
ctx.order.external_ids.vendor = "..."
line.price.unit_pp = new_price
ctx.order.subscriptions.append(subscription)
```

## Updating Parameters

The parameter bag exposes immutable helpers that return an updated copy instead
of mutating in place:

- `with_ordering_value(external_id, new_value)`
- `with_fulfillment_value(external_id, new_value)`
- `with_ordering_error(external_id, error)`
- `with_fulfillment_error(external_id, error)`
- `with_visibility(visible_params)`

Read-only access uses `get_ordering_value(external_id)` and
`get_fulfillment_value(external_id)`.

```python
updated_parameters = ctx.order.parameters.with_fulfillment_value("deploymentId", deployment_id)

await ctx.mpt_api_service.orders.update(
    ctx.order_id,
    attributes={"parameters": updated_parameters.to_dict()},
)
```

## Refreshing After A Write

When later code in the same flow must read the updated Marketplace
representation, refresh the snapshot explicitly. The SDK exposes two
mechanisms for orders:

- `await ctx.refresh_order()` reloads the canonical order from Marketplace.
- `@refresh_order` is a convenience decorator that refreshes the order after a
  step method returns successfully.

```python
from typing import override

from mpt_extension_sdk.pipeline import BaseStep, OrderContext, refresh_order


class CreateOrderSubscriptionsStep(BaseStep):
    @override
    @refresh_order
    async def process(self, ctx: OrderContext) -> None:
        await ctx.mpt_api_service.subscriptions.create_order_subscription(
            ctx.order_id,
            name="Example subscription",
            lines=[{"id": ctx.order.lines[0].id}],
        )
```

Agreement contexts expose the equivalent `await ctx.refresh_agreement()`
method.

Refresh adds an extra fetch, so use it only when the refreshed state is
actually required by a later step — for example after creating subscriptions or
assets inside an order. Do not refresh by default on every step.
