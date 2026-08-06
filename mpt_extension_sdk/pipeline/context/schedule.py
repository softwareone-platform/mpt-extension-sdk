import logging
from dataclasses import dataclass

from mpt_api_client.exceptions import MPTError

from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.services.mpt_api_service.task import TaskService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduleMetadata:
    """Immutable schedule execution metadata."""

    schedule_id: str
    task_id: str
    correlation_id: str | None = None


@dataclass(frozen=True)
class ScheduleTaskHandle:
    """Restricted Platform Task handle available to schedule handlers."""

    id: str
    task_service: TaskService

    async def progress(self, progress: float) -> None:
        """Report best-effort task progress to the platform.

        Args:
            progress: Progress value accepted by the Marketplace Tasks API.
        """
        try:
            await self.task_service.progress(self.id, progress)
        except MPTError as error:
            logger.warning("Could not report progress for task %s", self.id, exc_info=error)


@dataclass(kw_only=True)
class ScheduleContext(BaseContext):
    """Context provided to schedule handlers."""

    meta: ScheduleMetadata
    task: ScheduleTaskHandle
