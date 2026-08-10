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

`ScheduleRouter` exposes a `task(path, *, id, name, description, cron)` decorator to
register a periodic operation:

```python
from mpt_extension_sdk import ScheduleRouter

schedule_router = ScheduleRouter(prefix="/schedule")


@schedule_router.task(
    "/agreements/sync",
    id="schedule.agreements.sync",
    name="agreements-sync",
    description="Synchronize agreements periodically",
    cron="*/15 * * * *",
)
async def sync_agreements(ctx): ...
```

The SDK validates that the schedule `id` is unique within the extension and that
`cron` is a five-field expression, and emits each schedule into the generated
metadata under `schedules` (`id`, `name`, `description`, `cron`, `path`).

The runtime executes schedules: the Extension Framework delivers each schedule
occurrence to the SDK, which drives the delivery protocol. Every non-final task
responds with `Defer` on the watchdog cadence, and the event is only `OK`'d once
the task reaches a final state. The SDK then submits the handler to its
application-scoped runner.

See [schedules.md](schedules.md) for the full delivery protocol and handler guide.
