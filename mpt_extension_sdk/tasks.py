import logging
from dataclasses import dataclass
from typing import Any

from mpt_api_client.exceptions import MPTError
from pydantic import ValidationError

from mpt_extension_sdk.models.task import TaskLog, TaskLogSeverity, TaskParameters
from mpt_extension_sdk.services.mpt_api_service.task import TaskService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskHandle:
    """Platform Task id, logging, progress, and parameters, without access to the task lifecycle."""

    id: str
    task_service: TaskService

    async def log(
        self,
        message: str,
        severity: TaskLogSeverity = TaskLogSeverity.INFO,
        parameters: dict[str, Any] | None = None,  # noqa: WPS110
    ) -> None:
        """Write a best-effort log record to the platform task.

        Args:
            message: Log message, optionally a template with `{{Name}}` placeholders.
            severity: Severity of the log record.
            parameters: Values that fill the message template placeholders.
        """
        task_log = TaskLog(message=message, severity=severity, parameters=parameters)
        try:
            await self.task_service.create_log(self.id, task_log)
        except (MPTError, ValidationError) as error:
            logger.warning("Could not write log record for task %s", self.id, exc_info=error)

    async def progress(self, progress: float) -> None:
        """Report best-effort task progress to the platform.

        Args:
            progress: Progress value accepted by the Marketplace Tasks API.
        """
        try:
            await self.task_service.progress(self.id, progress)
        except MPTError as error:
            logger.warning("Could not report progress for task %s", self.id, exc_info=error)

    async def remove_parameter(self, name: str) -> None:
        """Remove a parameter from the platform task, keeping the others.

        Args:
            name: Parameter key, as sent to the platform.

        Raises:
            ValueError: When `name` is a reserved parameter.
            MPTError: When the task cannot be read or updated.
        """
        current = await self._get_parameters()
        await self._update_parameters(current, current.without_parameter(name))

    async def set_parameter(self, name: str, value: Any) -> None:  # noqa: WPS110
        """Add or overwrite a parameter on the platform task, keeping the others.

        Args:
            name: Parameter key, as sent to the platform.
            value: Parameter value.

        Raises:
            ValueError: When `name` is a reserved parameter.
            MPTError: When the task cannot be read or updated.
        """
        current = await self._get_parameters()
        await self._update_parameters(current, current.with_parameter(name, value))

    async def _get_parameters(self) -> TaskParameters:
        task = await self.task_service.get(self.id)
        return task.parameters or TaskParameters()

    async def _update_parameters(self, current: TaskParameters, changed: TaskParameters) -> None:
        if changed != current:
            await self.task_service.set_parameters(self.id, changed)
