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


FINAL_STATUSES = frozenset((TaskStatus.COMPLETED, TaskStatus.FAILED))


class TaskParameters(BaseModel):
    """Lifetime limits the platform publishes with a task."""

    max_task_processing_seconds: float | None = Field(
        default=None,
        serialization_alias="maxTaskProcessingSeconds",
        validation_alias="maxTaskProcessingSeconds",
    )
    max_task_lifetime_seconds: float | None = Field(
        default=None,
        serialization_alias="maxTaskLifetimeSeconds",
        validation_alias="maxTaskLifetimeSeconds",
    )


class Task(BaseModel):
    """Platform task tracked by a schedule execution."""

    id: str
    status: TaskStatus | str = Field(union_mode="left_to_right")
    audit: Audit | None = None
    parameters: TaskParameters | None = None  # noqa: WPS110

    @property
    def is_final(self) -> bool:
        """Whether the task has reached a final state."""
        return self.status in FINAL_STATUSES

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
