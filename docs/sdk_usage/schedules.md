# Schedule Routes

Use `ScheduleRouter` to register periodic work triggered by the Extension
Framework. The SDK publishes the cron configuration in extension metadata; it
does not run an in-process scheduler.

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
event from the body, and rejects a delivery that is missing either. Handlers read
the delivery through the schedule metadata:

| `ctx.meta` field | Source |
| --- | --- |
| `schedule_id` | The registered schedule identifier |
| `task_id` | The `MPT-Task-Id` header |
| `event_id` | The event identifier from the body |
| `enqueue_time` | When the framework enqueued the event |
| `correlation_id` | The request correlation identifier |

The event identifier is also part of the logging context, which is what joins an
extension log line with the framework worker log for the same delivery.

## Delivery protocol

The event is the durable timer of a schedule execution: every delivery of a
non-final task is answered with `Defer`, so the event returns later as a
watchdog. The event is only acknowledged with `OK` once its task has reached a
final state. The SDK decides each response from the platform task state:

| Task state on delivery | SDK action | Response |
| --- | --- | --- |
| `Queued` (first delivery) | Start task, submit handler | `Defer` (watchdog cadence) |
| `Rescheduled` | Start task, submit handler | `Defer` (watchdog cadence) |
| `Processing`, running in this process | None — this is the watchdog | `Defer` (watchdog cadence) |
| `Processing`, running elsewhere | None — the platform rejects the claim | `Defer` (watchdog cadence) |
| `Completed` / `Failed` | None | `OK` — the event is acknowledged |

The watchdog cadence is an exponential backoff derived from the elapsed
processing time, clamped between 5 and 30 minutes and capped by the event's
remaining retention, which is measured from the `enqueueTime` in the delivery
body. Near retention expiry the cap wins, so the delay can fall below the
5-minute minimum to keep the redelivery inside the retention window.

Authentication failures return `Cancel`, except on a task the SDK read as
final: the task state is read before authenticating, and a task already in a
final state is acknowledged with `OK`. The Extension Framework applies a
`Cancel` answer to the task even when the task is already `Completed`, so
answering `Cancel` there would record a successful execution as failed.

This narrows the window rather than closing it. A task that reaches a final
state after the SDK read it, and before the framework applies the answer, can
still be failed by a `Cancel`. The SDK cannot close that gap on its own: it
answers the delivery and the framework performs the transition, so there is no
SDK call to carry a precondition, and the Tasks API exposes no conditional
transition. Closing it belongs to the framework, which already rejects the same
transition with `409` when an extension attempts it.

Transient failures (task fetch, context creation, task start) return `Defer`
with the 5-minute default delay. If submission fails after the task starts, the
SDK reschedules the task and returns `Defer`.

## Claiming an execution

Starting the platform task is the claim. The platform accepts that transition
only from a retryable state, so it rejects every delivery of a task that is
already being executed, and the SDK answers the rejection with `Defer` at the
watchdog cadence.

A delivery can reach any instance of the extension, and any of its worker
processes. Keeping the claim in the platform is what limits a task to one
execution across all of them. The runner still reserves the task identifier
locally, but only to spare the round trip when a redelivery lands on the
process already running it. See [configuration.md](../configuration.md) for
the worker count settings.

## Delivery failures

A delivery the extension does not answer is retried by the Extension Framework
five times, about 120 seconds apart. When the last retry fails the event goes to
a dead-letter queue and the platform fails its task, roughly ten minutes after
the first delivery. Answering `Defer` is a successful delivery: it does not
consume the retry budget, it schedules the next watchdog instead.

An extension therefore has about two minutes to answer each delivery, and no
more than ten minutes of unanswered deliveries before the execution is lost.
This is why the SDK answers the delivery as soon as it has submitted the
handler, instead of holding the request open for the business logic.

## Schedule Tasks

Use `task(...)` to register a schedule handler. The SDK starts the platform
task, submits the handler to its application-scoped runner, and answers the
delivery without waiting for the business logic to finish.

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

For example, a full synchronization can process many agreements and report
progress without holding the schedule invocation open:

```python
@schedule_router.task(
    "/agreements/full-sync",
    id="agreements.full-sync",
    name="agreements-full-sync",
    description="Synchronize all agreements",
    cron="0 * * * *",
)
async def full_sync(ctx: ScheduleContext) -> None:
    agreements = await load_agreements(ctx)
    total = len(agreements)
    for position, agreement in enumerate(agreements, start=1):
        await synchronize_agreement(ctx, agreement)
        await ctx.task.progress(position / total * 100)
```

The developer does not call task lifecycle methods. The application-scoped
runner maps handler outcomes to platform task transitions:

- successful return: complete the task;
- `DeferError`: reschedule the task. This is a pure state transition — the
  task carries no timing. The handler is re-executed from the beginning on the
  next event delivery (watchdog cadence), so it must re-check its precondition
  on every execution and raise `DeferError` again if the condition still
  holds;
- `CancelError`, `FailError`, `ExtRuntimeError`, or an unexpected exception:
  apply `Cancel` response semantics, which transitions the platform task to
  `Failed`.

The platform publishes the task-lifetime limits under `parameters`:

```json
"parameters": {
  "extensionId": "EXT-7847-1229",
  "maxTaskProcessingSeconds": 7200,
  "maxTaskLifetimeSeconds": 86400
}
```

The SDK reads them from there, so it measures the same budget the platform
enforces. The Extension Framework does not accept per-schedule timeout
overrides, so these limits cannot be configured from the SDK.

Each limit is handled independently. A limit the task does not publish is logged
as an error and falls back to the SDK safety net — 2 hours of processing, a
24-hour total lifespan — while a limit the task does publish is still used as
sent. The safety net exists so a handler cannot run unbounded; it is not a copy
of the platform budget, and once it applies to a limit the SDK is no longer
guaranteed to finalize the task before the platform does.

The SDK uses the smaller of the two — counting the lifespan already consumed by
the task — minus a safety margin as its local execution deadline. If the handler
exceeds that deadline, the SDK fails the platform task with an explicit
processing timeout reason.

Operations that cannot reliably finish within the fixed processing budget must
make progress across separate cron occurrences: persist a progress cursor
outside the platform task, complete each task once its chunk is done, and let
the next occurrence resume with a fresh processing window. `DeferError` does not
extend the budget, since `Processing` and `Rescheduled` share the same clock.

Progress reporting is optional and best-effort. The SDK logs progress update
errors without failing the business operation. Progress does not extend the
task timeout limits.

Schedule identifiers must be unique within an extension. The SDK validates
this when routers are included and when extension metadata is validated.

Schedule handlers must be idempotent and must not rely on process-local state.
If an extension instance shuts down gracefully during execution, the SDK fails
the platform task with an explicit interruption reason and the next cron
occurrence executes normally.

After an abrupt termination (crash, OOM) no lifecycle call is possible and the
task stays in `Processing`. The SDK does not restart it, because a delivery
cannot tell a lost execution from one running in another process or instance.
The platform finalizes the task when it exceeds `maxTaskProcessingSeconds`, and
the following delivery finds it in `Failed` and acknowledges the event. The
interrupted occurrence is skipped rather than executed twice. The next cron
occurrence runs normally.
