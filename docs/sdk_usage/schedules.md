# Schedule Routes

Use `ScheduleRouter` to register periodic work triggered by the Extension
Framework. The SDK publishes the cron configuration in extension metadata; it
does not run an in-process scheduler.

## Registering a schedule

Use `task(...)` to register a schedule handler. The SDK runs it as a platform
Task (see [tasks.md](tasks.md)): it claims the Task, submits the handler to its
application-scoped runner, and answers the delivery without waiting for the
business logic to finish.

```python
from mpt_extension_sdk.pipeline import ScheduleContext
from mpt_extension_sdk.routing import ScheduleRouter

schedule_router = ScheduleRouter(prefix="/schedules")


@schedule_router.task(
    "/agreements/sync",
    id="agreements.sync",
    name="agreements-sync",
    description="Synchronize agreements",
    cron="*/15 * * * *",
)
async def sync_agreements(ctx: ScheduleContext) -> None:
    await synchronize_agreements(ctx)
```

The handler must be a coroutine function (`async def`), because it runs under
the task runner, which only accepts an awaitable. The SDK rejects a plain `def`
handler when the route is registered, so the mistake surfaces when the
extension starts.

Schedule identifiers must be unique within an extension. The SDK validates
this when routers are included and when extension metadata is validated.

## Task execution

A schedule runs as a platform Task. Handler outcomes, `ctx.task` reporting,
time limits, interruptions, and the delivery protocol are shared with every
task-based route and described in [tasks.md](tasks.md). This page covers only
what is specific to schedules.

## Schedule metadata

Handlers read the delivery through the schedule metadata:

| `ctx.meta` field | Source |
| --- | --- |
| `schedule_id` | The registered schedule identifier |
| `task_id` | The `MPT-Task-Id` header |
| `event_id` | The event identifier from the body |
| `enqueue_time` | When the framework enqueued the event |
| `correlation_id` | The request correlation identifier |

The event identifier is also part of the logging context, which is what joins an
extension log line with the framework worker log for the same delivery.

`ctx.task` reports progress, logs and parameters to the platform Task, as
described in [tasks.md](tasks.md#reporting-to-the-task).

## Long-running schedules

The Extension Framework does not accept per-schedule timeout overrides, so a
schedule runs within the limits the platform publishes on its Task (see
[tasks.md](tasks.md#time-limits)).

Operations that cannot reliably finish within the fixed processing budget must
make progress across separate cron occurrences: persist a progress cursor
outside the platform task, complete each task once its chunk is done, and let
the next occurrence resume with a fresh processing window.

An occurrence interrupted by a shutdown or a crash is not run again (see
[tasks.md](tasks.md#idempotency-and-interruptions)); the next cron occurrence
executes normally.

## Delivery body

The Extension Framework delivers a schedule as a task event, and also provides
the platform task identifier in the `MPT-Task-Id` header:

```json
{
  "id": "e5b68484-42a3-4e8a-a699-ad4b4e029745",
  "object": {
    "id": "agreements.sync",
    "name": "agreements-sync",
    "objectType": "Schedule"
  },
  "task": {"id": "TSK-0014-2070-1237-2512"},
  "details": {
    "enqueueTime": "2026-08-11T17:04:00.000Z",
    "deliveryTime": "2026-08-11T17:04:00.514Z",
    "eventType": "Schedule"
  }
}
```

Both are required: the SDK takes the task identifier from the header and the
event from the body, and rejects a delivery that is missing either. The SDK
answers each delivery following the
[delivery protocol](tasks.md#delivery-protocol).
