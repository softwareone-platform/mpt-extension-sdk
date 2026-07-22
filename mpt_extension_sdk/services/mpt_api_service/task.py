from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class TaskService(BaseService[Task]):
    """Task service."""

    async def get(self, task_id: str) -> Task:
        """Fetch a platform task.

        Args:
            task_id: Unique identifier of the platform task.
        """
        return Task.from_payload(await self._client.system.tasks.get(task_id))

    async def complete(self, task_id: str) -> None:
        """Signal the platform that a task has been processed successfully.

        Args:
            task_id: Unique identifier of the platform task.
        """
        await self._client.system.tasks.complete(task_id, {})

    async def fail(self, task_id: str, reason: str | None = None) -> None:
        """Signal the platform that a task has failed.

        Args:
            task_id: Unique identifier of the platform task.
            reason: Optional failure reason to include in the task log.
        """
        if reason is None:
            await self._client.system.tasks.fail(task_id)
            return
        await self._client.system.tasks.fail(task_id, {"reason": reason})

    async def progress(self, task_id: str, progress: float) -> None:
        """Update the progress of a task."""
        await self._client.system.tasks.update(task_id, {"progress": progress})

    async def reschedule(self, task_id: str) -> None:
        """Move a task back to a retryable status.

        This is a pure state transition: redelivery timing is controlled by the
        event Defer responses, not by the task.

        Args:
            task_id: Unique identifier of the platform task.
        """
        await self._client.system.tasks.reschedule(task_id)

    async def start(self, task_id: str) -> None:
        """Signal the platform that processing of a task has started.

        Args:
            task_id: Unique identifier of the platform task.
        """
        await self._client.system.tasks.execute(task_id)
