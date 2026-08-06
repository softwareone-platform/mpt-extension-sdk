import datetime as dt

from mpt_extension_sdk.models.task import Task

# Schedules run at the platform's fixed task-lifetime defaults; the Extension
# Framework does not accept per-schedule timeout overrides.
DEFAULT_MAX_TASK_LIFESPAN = 86400
DEFAULT_MAX_TASK_PROCESSING = 7200
TASK_TIMEOUT_SAFETY_MARGIN = 60

EVENT_RETENTION_SECONDS = 604800
MIN_WATCHDOG_DELAY_SECONDS = 300
MAX_WATCHDOG_DELAY_SECONDS = 1800


def watchdog_delay_seconds(task: Task) -> int:
    """Return the delay until the event should be redelivered."""
    now = dt.datetime.now(dt.UTC)
    elapsed = _elapsed_seconds(task.started_at, now)
    remaining_retention = EVENT_RETENTION_SECONDS - _elapsed_seconds(task.created_at, now)
    delay = min(
        max(elapsed, MIN_WATCHDOG_DELAY_SECONDS),
        MAX_WATCHDOG_DELAY_SECONDS,
        remaining_retention - TASK_TIMEOUT_SAFETY_MARGIN,
    )
    return max(int(delay), TASK_TIMEOUT_SAFETY_MARGIN)


def get_execution_deadline(task: Task) -> float:
    """Return the local execution deadline before platform auto-finalization.

    Schedules run at the platform's fixed task-lifetime defaults; per-schedule
    overrides are not accepted by the Extension Framework.
    """
    now = dt.datetime.now(dt.UTC)
    remaining_lifespan = DEFAULT_MAX_TASK_LIFESPAN - _elapsed_seconds(task.created_at, now)
    timeout_limit = min(DEFAULT_MAX_TASK_PROCESSING, remaining_lifespan)
    return max(timeout_limit - TASK_TIMEOUT_SAFETY_MARGIN, 1)


def _elapsed_seconds(timestamp: dt.datetime | None, now: dt.datetime) -> float:
    """Return the seconds elapsed since a timestamp, or 0 when unknown."""
    if timestamp is None:
        return 0
    return (now - timestamp).total_seconds()
