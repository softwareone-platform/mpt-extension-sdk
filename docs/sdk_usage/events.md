# Event Routes

Use `EventRouter` when the extension needs to handle platform events.

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

## Schedule Routes

`ScheduleRouter` exists in the SDK contract and exposes a `schedule(path, name)`
decorator, but scheduled routes are out of scope for the current phase: they are
not yet mounted by the runtime nor emitted into the generated metadata. Treat
`ScheduleRouter` as a forward-looking placeholder and do not rely on it for
production flows yet.
