import datetime as dt
import logging

from mpt_extension_sdk.models.task import Task, TaskParameters

logger = logging.getLogger(__name__)

# Local safety net, not a copy of the platform limit. The deadline is normally the one
# the task publishes; these values only cap an execution whose task published nothing,
# so a handler cannot run unbounded. The Extension Framework does not accept
# per-schedule timeout overrides.
FALLBACK_MAX_TASK_LIFESPAN = 86400
FALLBACK_MAX_TASK_PROCESSING = 7200
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

    The limits are the ones the platform publishes with the task, so the SDK and the
    platform measure the same budget. A task that publishes no limit falls back to the
    SDK safety net, which caps the execution but does not mirror the platform budget.
    """
    now = dt.datetime.now(dt.UTC)
    limits = task.parameters or TaskParameters()
    remaining_processing = _remaining_budget(
        limits.max_task_processing_seconds,
        FALLBACK_MAX_TASK_PROCESSING,
        "maxTaskProcessingSeconds",
        _elapsed_seconds(task.started_at, now),
    )
    remaining_lifespan = _remaining_budget(
        limits.max_task_lifetime_seconds,
        FALLBACK_MAX_TASK_LIFESPAN,
        "maxTaskLifetimeSeconds",
        _elapsed_seconds(task.created_at, now),
    )
    return max(min(remaining_processing, remaining_lifespan) - TASK_TIMEOUT_SAFETY_MARGIN, 1)


def delivery_latency_seconds(enqueued_at: dt.datetime, delivered_at: dt.datetime) -> float:
    """Return how long the framework held the event before delivering it.

    Args:
        enqueued_at: When the framework enqueued the event.
        delivered_at: When the framework delivered it to the extension.

    Returns:
        The seconds between the two timestamps.
    """
    return (delivered_at - enqueued_at).total_seconds()


def _remaining_budget(
    published: float | None, fallback: int, field_name: str, elapsed: float
) -> float:
    """Return what is left of a published limit, or of the safety net when it is absent."""
    if published is None:
        logger.error(
            "Task did not publish %s: the deadline no longer tracks the platform budget, "
            "capping the execution at the %s second safety net",
            field_name,
            fallback,
        )
        published = fallback
    return published - elapsed


def _elapsed_seconds(timestamp: dt.datetime | None, now: dt.datetime) -> float:
    """Return the seconds elapsed since a timestamp, or 0 when unknown."""
    if timestamp is None:
        return 0
    return (now - timestamp).total_seconds()
