import logging

from mpt_api_client.exceptions import MPTAPIError, MPTHttpError

from mpt_extension_sdk.errors.mapping import map_exception_to_event_response
from mpt_extension_sdk.errors.pipeline import DeferError
from mpt_extension_sdk.services.mpt_api_service.task import TaskService

FINALIZED_TASK_STATUS_CODES = frozenset((404, 409))


class SafeTaskTransitions:
    """Platform Task lifecycle transitions tolerant of finalized-task rejections.

    Each transition ignores the lifecycle rejections the platform raises once it
    has already finalized the task (404/409), so a late transition does not turn
    into an error.
    """

    def __init__(self, task_service: TaskService, handler_logger: logging.Logger) -> None:
        """Initialize the transitions with their collaborators."""
        self.task_service = task_service
        self.handler_logger = handler_logger

    async def complete(self, task_id: str) -> None:
        """Complete a task and ignore final-state lifecycle rejections."""
        try:
            await self.task_service.complete(task_id)
        except (MPTHttpError, MPTAPIError) as error:
            self._log_finalized_rejection(task_id, error)

    async def fail(self, task_id: str, reason: str | None = None) -> None:
        """Fail a task and ignore final-state lifecycle rejections."""
        try:
            await self.task_service.fail(task_id, reason=reason)
        except (MPTHttpError, MPTAPIError) as error:
            self._log_finalized_rejection(task_id, error)

    async def reschedule(self, task_id: str) -> None:
        """Reschedule a task and ignore final-state lifecycle rejections."""
        try:
            await self.task_service.reschedule(task_id)
        except (MPTHttpError, MPTAPIError) as error:
            self._log_finalized_rejection(task_id, error)

    async def transition_on_error(self, task_id: str, error: Exception) -> None:
        """Map a handler error to its platform task transition."""
        if isinstance(error, DeferError):
            # The retry happens on the next event delivery; the task carries no timing.
            self.handler_logger.info("Async task %s rescheduled", task_id)
            await self.reschedule(task_id)
            return

        outcome = map_exception_to_event_response(error)
        self.handler_logger.info("Async task %s cancelled: %s", task_id, outcome.cancel_reason)
        # A Cancel event outcome transitions a task-based execution to Failed.
        await self.fail(task_id, reason=outcome.cancel_reason)

    def _log_finalized_rejection(self, task_id: str, error: MPTHttpError | MPTAPIError) -> None:
        """Log lifecycle rejections caused by already-finalized platform tasks."""
        status_code = getattr(error, "status_code", None)
        if status_code in FINALIZED_TASK_STATUS_CODES:
            self.handler_logger.warning(
                "Lifecycle transition for task %s was rejected because the task is final",
                task_id,
            )
            return
        raise error
