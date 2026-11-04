# Task-Based Execution

A task handler runs as a platform Task. The SDK claims the Task, submits the
handler to its application-scoped runner, and answers the delivery without
waiting for the business logic to finish. The Task, not the HTTP request,
carries the execution.

This page describes what every task handler shares. Each route guide says which
of its handlers run as tasks and what is specific to them.

## Handler outcomes

The developer does not call task lifecycle methods. The runner maps the handler
outcome to a platform Task transition:

- successful return: complete the Task;
- `DeferError`: reschedule the Task. This is a pure state transition: the Task
  carries no timing, and `delay_seconds` is not used. The handler runs again
  from the beginning on the next delivery (watchdog cadence), so it must
  re-check its precondition on every execution and raise `DeferError` again if
  the condition still holds;
- `CancelError`, `FailError`, `ExtRuntimeError`, or an unexpected exception:
  apply `Cancel` response semantics, which transitions the platform Task to
  `Failed`.

Each outcome is logged once on the handler logger: a successful return at info
level, a reschedule or a `CancelError` at info level with its reason, and any
other error at error level with the failure reason and its traceback.

See [error-handling.md](error-handling.md#raising-errors-from-steps) for how
step errors become these exceptions.

## Reporting to the task

A handler whose context carries a `TaskHandle` as `ctx.task` reports to its
platform Task through it, so whoever follows the Task in the platform sees what
the operation is doing and why it ended the way it did:

- `ctx.task.progress(...)` updates the Task progress;
- `ctx.task.log(...)` writes a Task Log Record. The severity is `Info` by
  default; pass any `TaskLogSeverity` value (`Debug`, `Info`, `Warning`,
  `Error`, or `Failure`) to change it, and `parameters` to fill the `{{Name}}`
  placeholders of the message template.

For example, a full synchronization can process many agreements and report
what it is doing without holding the delivery open:

```python
from mpt_extension_sdk.models import TaskLogSeverity


async def full_sync(ctx) -> None:
    agreements = await load_agreements(ctx)
    total = len(agreements)
    for position, agreement in enumerate(agreements, start=1):
        await ctx.task.log(
            "Synchronizing agreement '{{AgreementId}}'",
            parameters={"AgreementId": agreement.id},
        )
        if not await synchronize_agreement(ctx, agreement):
            await ctx.task.log(
                "Agreement '{{AgreementId}}' was skipped",
                severity=TaskLogSeverity.WARNING,
                parameters={"AgreementId": agreement.id},
            )
        await ctx.task.progress(position / total * 100)
```

Progress reporting and task logging are optional and best-effort. When the
platform call fails with an `MPTError`, or a created log record cannot be read
back, the SDK logs it locally, the handler keeps running, and the Task outcome
is unchanged. Other exceptions propagate to the handler. Neither extends the
Task time limits.

`ctx.task.set_parameter(name, value)` adds a parameter to the Task, or
overwrites it, and `ctx.task.remove_parameter(name)` removes one:

```python
await ctx.task.set_parameter("syncCursor", agreement.id)
```

The platform replaces the whole `parameters` object on every update, so each
parameter call reads the Task, changes that one parameter, and writes back all
of them. The other parameters are kept, but two writers on the same Task at the
same time can overwrite each other's change. `extensionId`,
`maxTaskProcessingSeconds`, and `maxTaskLifetimeSeconds` are published by the
platform (see [Time limits](#time-limits)): setting or removing them raises
`ValueError` and the Task is not updated. Unlike progress and logging, the
parameter calls are not best-effort: an `MPTError` from reading or updating the
Task propagates to the handler. They do not extend the Task time limits either.

## Time limits

The platform publishes the task-lifetime limits under `parameters`:

```json
"parameters": {
  "extensionId": "EXT-7847-1229",
  "maxTaskProcessingSeconds": 7200,
  "maxTaskLifetimeSeconds": 86400
}
```

The SDK reads them from there, so it measures the same budget the platform
enforces.

Each limit is handled independently. A limit the Task does not publish is
logged as an error and falls back to the SDK safety net — 2 hours of
processing, a 24-hour total lifespan — while a limit the Task does publish is
still used as sent. The safety net exists so a handler cannot run unbounded; it
is not a copy of the platform budget, and once it applies to a limit the SDK is
no longer guaranteed to finalize the Task before the platform does.

The SDK uses the smaller of the two — counting the lifespan already consumed by
the Task — minus a safety margin as its local execution deadline. If the
handler exceeds that deadline, the SDK fails the platform Task with an explicit
processing timeout reason. `DeferError` does not extend the budget, since
`Processing` and `Rescheduled` share the same clock.

## Idempotency and interruptions

Task handlers must be idempotent and must not rely on process-local state. If
an extension instance shuts down gracefully during execution, the SDK cancels
the handler and fails the platform Task with an explicit interruption reason.

After an abrupt termination (crash, OOM) no lifecycle call is possible and the
Task stays in `Processing`. The SDK does not restart it, because a delivery
cannot tell a lost execution from one running in another process or instance.
The platform finalizes the Task when it exceeds `maxTaskProcessingSeconds`, and
the following delivery finds it in `Failed` and acknowledges the event. The
interrupted execution is skipped rather than run twice.

## Delivery protocol

The rest of this page describes how the SDK answers task deliveries. A handler
does not depend on it directly.

The delivery is the durable timer of a Task execution: every accepted delivery
of a non-final Task is answered with `Defer`, so it returns later as a
watchdog. The delivery is only acknowledged with `OK` once its Task has reached
a final state. Authentication failures and non-recoverable context errors are
answered with `Cancel` instead, as described below. The SDK decides each
response from the platform Task state:

| Task state on delivery | SDK action | Response |
| --- | --- | --- |
| `Queued` (first delivery) | Start Task, submit handler | `Defer` (watchdog cadence) |
| `Rescheduled` | Start Task, submit handler | `Defer` (watchdog cadence) |
| `Processing`, running in this process | None — this is the watchdog | `Defer` (watchdog cadence) |
| `Processing`, running elsewhere | None — the Task is not claimed and the handler is not called | `Defer` (watchdog cadence) |
| `Completed` / `Failed` | None | `OK` — the delivery is acknowledged |
| `Queued` / `Rescheduled`, this process at `SDK_MAX_CONCURRENT_TASKS` | None — the Task is not claimed | `Defer` (watchdog cadence) |

The watchdog cadence answers a delay equal to the processing time elapsed so
far, clamped between 5 and 30 minutes, so the interval between deliveries
doubles until it reaches 30 minutes. When the delivery body carries an event,
the cadence is also capped by the event's remaining retention, measured from
its `enqueueTime`. Near retention expiry the
cap wins, so the delay can fall below the 5-minute minimum to keep the
redelivery inside the retention window.

Authentication failures return `Cancel`, except on a Task the SDK read as
final: the Task state is read before authenticating, and a Task already in a
final state is acknowledged with `OK`. The Extension Framework applies a
`Cancel` answer to the Task even when the Task is already `Completed`, so
answering `Cancel` there would record a successful execution as failed.

This narrows the window rather than closing it. A Task that reaches a final
state after the SDK read it, and before the framework applies the answer, can
still be failed by a `Cancel`. The SDK cannot close that gap on its own: it
answers the delivery and the framework performs the transition, so there is no
SDK call to carry a precondition, and the Tasks API exposes no conditional
transition. Closing it belongs to the framework, which already rejects the same
transition with `409` when an extension attempts it.

A context the SDK cannot build for a reason that will not change on
redelivery — a configuration or validation error, or a context adapter that
rejects the context — returns `Cancel`. Transient failures (Task fetch, context
creation, Task start) return `Defer` with the 5-minute default delay. If
submission fails after the Task starts, the SDK reschedules the Task and
returns `Defer`.

### Claiming an execution

Starting the platform Task is the claim. The platform accepts that transition
only from a retryable state, so a Task that is already being executed cannot be
claimed again. A delivery that finds the Task in `Processing` on a process that
is not running it is therefore answered with `Defer` at the watchdog cadence
without building the handler context, calling the handler, or changing the
Task state. A claim the platform still rejects, because another execution
claimed the Task after the SDK read it, gets the same answer.

Every claimed Task records the instance that ran it in its `instanceId`
parameter. Recording it is best-effort: a failure is logged as a warning and
the claim still counts.

A delivery can reach any instance of the extension, and any of its worker
processes. Keeping the claim in the platform is what limits a Task to one
execution across all of them. The runner still reserves the Task identifier
locally, but only to spare the round trip when a redelivery lands on the
process already running it. `SDK_MAX_CONCURRENT_TASKS` limits every task
execution of the process together; see
[configuration.md](../configuration.md) for it and the worker count settings.

### Delivery failures

A delivery the extension does not answer is retried by the Extension Framework
five times, about 120 seconds apart. When the last retry fails the event goes to
a dead-letter queue and the platform fails its Task, roughly ten minutes after
the first delivery. Answering `Defer` is a successful delivery: it does not
consume the retry budget, it schedules the next watchdog instead.

An extension therefore has about two minutes to answer each delivery, and no
more than ten minutes of unanswered deliveries before the execution is lost.
This is why the SDK answers the delivery as soon as it has submitted the
handler, instead of holding the request open for the business logic.
