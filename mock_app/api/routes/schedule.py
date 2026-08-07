import asyncio

from mpt_extension_sdk.errors.pipeline import CancelError, DeferError
from mpt_extension_sdk.pipeline import ScheduleContext
from mpt_extension_sdk.routing import ScheduleRouter

schedule_router = ScheduleRouter(prefix="/schedules")

# Longer than the accelerated processing budget the devmock publishes with the
# task (`maxTaskProcessingSeconds`, 120s), so the SDK deadline fires first.
TIMEOUT_DEMO_SLEEP_SECONDS = 180
HALFWAY_PROGRESS = 50
FULL_PROGRESS = 100


@schedule_router.task(
    "/use-cases/ok",
    id="mock.use-cases.ok",
    name="schedule-use-case-ok",
    description="Report progress, then complete successfully",
    cron="*/5 * * * *",
)
async def handle_ok(ctx: ScheduleContext) -> None:
    """Report progress, then return normally so the SDK completes the platform task.

    Progress is best-effort: a failed report neither fails the handler nor extends
    the task lifetime limits.
    """
    await ctx.task.progress(HALFWAY_PROGRESS)
    await asyncio.sleep(1)
    await ctx.task.progress(FULL_PROGRESS)
    ctx.logger.info("Schedule ok: task %s reported progress and completed", ctx.meta.task_id)


@schedule_router.task(
    "/use-cases/cancel",
    id="mock.use-cases.cancel",
    name="schedule-use-case-cancel",
    description="Fail the task by raising CancelError",
    cron="*/3 * * * *",
)
async def handle_cancel(ctx: ScheduleContext) -> None:  # ruff:ignore[unused-async] - schedule handlers are async by contract
    """Raise CancelError so the SDK fails the platform task."""
    ctx.logger.info("Schedule cancel: task %s will be failed", ctx.meta.task_id)
    raise CancelError("Cancelled by the schedule handler")


@schedule_router.task(
    "/use-cases/defer",
    id="mock.use-cases.defer",
    name="schedule-use-case-defer",
    description="Reschedule the task by raising DeferError",
    cron="*/2 * * * *",
)
async def handle_defer(ctx: ScheduleContext) -> None:  # ruff:ignore[unused-async] - schedule handlers are async by contract
    """Raise DeferError so the SDK reschedules the platform task.

    The precondition never clears, so the event is redelivered on the watchdog
    cadence and never acknowledged. The handler restarts from the beginning every
    time, which is why it must re-check its precondition on each delivery.
    """
    ctx.logger.info("Schedule defer: task %s will be rescheduled", ctx.meta.task_id)
    raise DeferError("Prerequisite not ready; retry on the next delivery")


@schedule_router.task(
    "/use-cases/timeout",
    id="mock.use-cases.timeout",
    name="schedule-use-case-timeout",
    description="Exceed maxTaskProcessing so the SDK fails the task on its deadline",
    cron="*/1 * * * *",
)
async def handle_timeout(ctx: ScheduleContext) -> None:
    """Sleep past the local execution deadline so the SDK fails the task on timeout.

    Redeliveries while it sleeps are deferred, because the platform rejects the
    claim on a task already being executed, whichever instance or worker process
    they reach.
    """
    ctx.logger.info("Schedule timeout: task %s sleeps past its deadline", ctx.meta.task_id)
    await asyncio.sleep(TIMEOUT_DEMO_SLEEP_SECONDS)
