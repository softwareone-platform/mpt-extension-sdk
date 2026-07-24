import datetime as dt
from typing import Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models.audit import Audit
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)


class UnknownTaskStatusWarning(UnknownStatusWarning):
    """Signals that a platform task reported a status outside the known set."""


class TaskStatus(CaseInsensitiveStrEnum):
    """Known Platform Task statuses used by schedule execution."""

    COMPLETED = "completed"
    FAILED = "failed"
    PROCESSING = "processing"
    QUEUED = "queued"
    RESCHEDULED = "rescheduled"


ACTIVE_STATUSES = frozenset((TaskStatus.PROCESSING,))
FINAL_STATUSES = frozenset((TaskStatus.COMPLETED, TaskStatus.FAILED))


class Task(BaseModel):
    """Platform task tracked by a schedule execution."""

    id: str
    status: TaskStatus | str = Field(union_mode="left_to_right")
    audit: Audit | None = None

    @property
    def is_final(self) -> bool:
        """Whether the task has reached a final state."""
        return self.status in FINAL_STATUSES

    @property
    def is_processing(self) -> bool:
        """Whether the task is in an active processing state."""
        return self.status in ACTIVE_STATUSES

    @property
    def created_at(self) -> dt.datetime | None:
        """The task creation time, if available."""
        created = self.audit.created if self.audit else None
        return created.timestamp if created else None

    @property
    def started_at(self) -> dt.datetime | None:
        """The last transition to processing, if available."""
        started = self.audit.started if self.audit else None
        return started.timestamp if started else None

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known TaskStatus."""
        warn_on_unknown_status("Task", self.id, self.status, TaskStatus, UnknownTaskStatusWarning)
        return self
