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

Use `task(...)` for task-backed events. The runtime runs the handler as a
platform Task on its application-scoped runner, outside the HTTP request, and
completes, fails, or reschedules the Task from the handler outcome.

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

Handler outcomes, time limits, interruptions, `SDK_MAX_CONCURRENT_TASKS`, and
the delivery protocol are shared with every task-based route and described in
[tasks.md](tasks.md). What is specific to task-backed events:

- the Task identifier comes from `task.id` in the event body, and the context
  exposes it as `ctx.meta.task_id`; the context has no `ctx.task` handle;
- the Task runs within the time limits the platform publishes on it;
- the context adapter and the event span work as for non-task events, and the
  span covers the handler execution in the runner.

The mock app's `orders-change`
([`mock_app/api/routes/event.py`](../../mock_app/api/routes/event.py)) is a working
example. Run it locally as described in
[`peripherals/devmock/README.md`](../../peripherals/devmock/README.md#task-based-events).

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

The runtime executes schedules as platform Tasks. See
[schedules.md](schedules.md) for the schedule guide and
[tasks.md](tasks.md) for the delivery protocol.
