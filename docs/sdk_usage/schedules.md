# Schedule Routes

Use `ScheduleRouter` to register periodic work triggered by the Extension
Framework. The SDK publishes the cron configuration in extension metadata; it
does not run an in-process scheduler.

The Extension Framework invokes schedule endpoints without a request body and
provides the platform task identifier through the `MPT-Task-Id` header.

## Delivery protocol

The event is the durable timer of a schedule execution: every delivery of a
non-final task is answered with `Defer`, so the event returns later as a
watchdog. The event is only acknowledged with `OK` once its task has reached a
final state. The SDK decides each response from the platform task state:

| Task state on delivery | SDK action | Response |
| --- | --- | --- |
| `Queued` (first delivery) | Start task, submit handler | `Defer` (watchdog cadence) |
| `Rescheduled` | Start task, submit handler | `Defer` (watchdog cadence) |
| `Processing`, running in this instance | None — this is the watchdog | `Defer` (watchdog cadence) |
| `Processing`, not running in this instance | Lost execution: reschedule, start, submit handler | `Defer` (watchdog cadence) |
| `Completed` / `Failed` | None | `OK` — the event is acknowledged |

The watchdog cadence is an exponential backoff derived from the elapsed
processing time, clamped between 5 and 30 minutes and capped by the event's
remaining retention.

Authentication failures return `Cancel`. Transient failures (task fetch,
context creation, task start) return `Defer` with the 5-minute default delay.
If submission fails after the task starts, the SDK reschedules the task and
returns `Defer`.

The runner reserves the task identifier synchronously before context creation.
Concurrent delivery of the same task identifier therefore cannot start or
submit the task twice; the extra delivery is answered with `Defer`, keeping
the watchdog alive. Failed acceptance releases the reservation.

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

Schedules run at the platform's fixed task-lifetime defaults: 2 hours of
processing (`maxTaskProcessing`) and a 24-hour total lifespan
(`maxTaskLifespan`). The Extension Framework does not accept per-schedule
timeout overrides, so these limits cannot be configured from the SDK. The SDK
uses the smaller of the two — counting the lifespan already consumed by the
task — minus a safety margin as its local execution deadline. If the handler
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
occurrence executes normally. After an abrupt termination (crash, OOM), the
next watchdog delivery finds the task in `Processing` without a local
execution and restarts it, re-executing the handler from the beginning.
