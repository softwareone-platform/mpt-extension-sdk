import datetime as dt
from dataclasses import dataclass

from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.tasks import TaskHandle

ScheduleTaskHandle = TaskHandle


@dataclass(frozen=True)
class ScheduleMetadata:
    """Immutable schedule execution metadata."""

    enqueue_time: dt.datetime
    event_id: str
    schedule_id: str
    task_id: str
    correlation_id: str | None = None


@dataclass(kw_only=True)
class ScheduleContext(BaseContext):
    """Context provided to schedule handlers."""

    meta: ScheduleMetadata
    task: TaskHandle
