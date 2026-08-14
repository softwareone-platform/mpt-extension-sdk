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


def watchdog_delay_seconds(task: Task, *, enqueued_at: dt.datetime) -> int:
    """Return the delay until the event should be redelivered.

    The delay never removes the safety margin from the event's remaining
    retention, so the watchdog is always scheduled before the event expires.
    Near retention expiry this can fall below the normal minimum cadence to
    keep the redelivery inside the retention window.

    Args:
        task: The platform task of the delivery.
        enqueued_at: When the framework enqueued the event, from the delivery body.

    Returns:
        The number of seconds to ask for in the Delay answer.
    """
    now = dt.datetime.now(dt.UTC)
    elapsed = _elapsed_seconds(task.started_at, now)
    remaining_retention = EVENT_RETENTION_SECONDS - _elapsed_seconds(enqueued_at, now)
    schedulable = remaining_retention - TASK_TIMEOUT_SAFETY_MARGIN
    delay = min(
        max(elapsed, MIN_WATCHDOG_DELAY_SECONDS),
        MAX_WATCHDOG_DELAY_SECONDS,
        schedulable,
    )
    return max(int(delay), 1)


def get_execution_deadline(task: Task) -> float:
    """Return the local execution deadline before platform auto-finalization.

    Schedules run at the platform's fixed task-lifetime defaults; per-schedule
    overrides are not accepted by the Extension Framework.
    """
    now = dt.datetime.now(dt.UTC)
    remaining_processing = DEFAULT_MAX_TASK_PROCESSING - _elapsed_seconds(task.started_at, now)
    remaining_lifespan = DEFAULT_MAX_TASK_LIFESPAN - _elapsed_seconds(task.created_at, now)
    timeout_limit = min(remaining_processing, remaining_lifespan)
    return max(timeout_limit - TASK_TIMEOUT_SAFETY_MARGIN, 1)


def delivery_latency_seconds(enqueued_at: dt.datetime, delivered_at: dt.datetime) -> float:
    """Return how long the framework held the event before delivering it.

    Args:
        enqueued_at: When the framework enqueued the event.
        delivered_at: When the framework delivered it to the extension.

    Returns:
        The seconds between the two timestamps.
    """
    return (delivered_at - enqueued_at).total_seconds()


def _elapsed_seconds(timestamp: dt.datetime | None, now: dt.datetime) -> float:
    """Return the seconds elapsed since a timestamp, or 0 when unknown."""
    if timestamp is None:
        return 0
    return (now - timestamp).total_seconds()
