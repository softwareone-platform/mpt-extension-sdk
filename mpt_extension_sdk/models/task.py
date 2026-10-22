import datetime as dt
from typing import Any, Self, override

from pydantic import Field, model_validator

from mpt_extension_sdk.models.audit import Audit
from mpt_extension_sdk.models.base import BaseModel, ISODatetime
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


class TaskLogSeverity(CaseInsensitiveStrEnum):
    """Severities of a platform Task Log Record."""

    DEBUG = "Debug"
    ERROR = "Error"
    FAILURE = "Failure"
    INFO = "Info"  # noqa: WPS110
    WARNING = "Warning"


FINAL_STATUSES = frozenset((TaskStatus.COMPLETED, TaskStatus.FAILED))


class TaskParameters(BaseModel):
    """Task parameters: the reserved ones the platform publishes, plus free-form ones.

    The declared fields are reserved: `with_parameter` and `without_parameter`
    refuse to change them. Any other key is kept as an extra parameter.
    """

    extension_id: str | None = Field(
        default=None,
        serialization_alias="extensionId",
        validation_alias="extensionId",
    )
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

    @override
    def to_dict(self) -> dict[str, Any]:
        """Dump the parameters, leaving out reserved ones the task does not have."""
        parameters = self.model_dump(mode="json")  # noqa: WPS110
        for field_name, field in type(self).model_fields.items():
            if getattr(self, field_name) is None:
                parameters.pop(field.serialization_alias or field_name)
        return parameters

    def with_parameter(self, name: str, value: Any) -> Self:  # noqa: WPS110
        """Return a copy with the parameter added, or overwritten when it exists.

        Args:
            name: Parameter key, as sent to the platform.
            value: Parameter value.

        Raises:
            ValueError: When `name` is a reserved parameter.
        """
        self._ensure_not_reserved(name)
        return self.model_validate({**self.to_dict(), name: value})

    def without_parameter(self, name: str) -> Self:
        """Return a copy without the parameter; a missing parameter is ignored.

        Args:
            name: Parameter key, as sent to the platform.

        Raises:
            ValueError: When `name` is a reserved parameter.
        """
        self._ensure_not_reserved(name)
        parameters = self.to_dict()  # noqa: WPS110
        parameters.pop(name, None)
        return self.model_validate(parameters)

    def _ensure_not_reserved(self, name: str) -> None:
        for field_name, field in type(self).model_fields.items():
            if name in {field_name, field.serialization_alias}:
                raise ValueError(f"Task parameter '{name}' is reserved and cannot be changed")


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


class TaskReference(BaseModel):
    """Task reference."""

    id: str


class TaskLog(BaseModel):
    """Platform Task Log Record describing what a task is doing."""

    id: str | None = None
    eta: ISODatetime | None = None
    message: str
    parameters: dict[str, Any] | None = None  # noqa: WPS110
    progress: float | None = None
    severity: TaskLogSeverity = TaskLogSeverity.INFO
    task: TaskReference | None = None
    timestamp: ISODatetime | None = None
