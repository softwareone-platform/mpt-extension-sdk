import logging

from mpt_api_client.exceptions import MPTError

from mpt_extension_sdk.api.auth import AuthenticationError
from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.errors.runtime import ConfigError, ValidationError
from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.runtime.task_transitions import TASK_CONFLICT_STATUS_CODE
from mpt_extension_sdk.services.mpt_api_service.task import TaskService

NON_RECOVERABLE_CONTEXT_ERRORS = (ConfigError, ValidationError, TypeError, ValueError)
CONTEXT_CREATION_ERRORS = (AuthenticationError, *NON_RECOVERABLE_CONTEXT_ERRORS, MPTError)


class ScheduleTaskAcceptance:
    """Platform Task lifecycle operations that defer the delivery on infrastructure failures."""

    def __init__(self, *, task_service: TaskService, handler_logger: logging.Logger) -> None:
        """Initialize the acceptance operations with their collaborators."""
        self.task_service = task_service
        self.handler_logger = handler_logger

    async def fetch_task(self, task_id: str) -> Task | None:
        """Fetch the platform task, deferring the delivery when unavailable."""
        try:
            return await self.task_service.get(task_id)
        except MPTError as error:
            self.handler_logger.exception("Could not fetch schedule task", exc_info=error)
            return None

    async def start_task(self, task_id: str, *, watchdog_delay: int) -> EventResponse | None:
        """Claim a platform task and return a deferring response when it is not claimed.

        Starting the task is the claim: the platform only accepts the transition from a
        retryable state, so it rejects with a conflict every delivery of a task that is
        already being executed, whichever worker process or instance the delivery lands on.

        Args:
            task_id: Unique identifier of the platform task.
            watchdog_delay: Delay to answer with when another execution holds the task.

        Returns:
            None when this delivery claimed the task, otherwise the deferring response.
        """
        try:
            await self.task_service.start(task_id)
        except MPTError as error:
            if getattr(error, "status_code", None) == TASK_CONFLICT_STATUS_CODE:
                self.handler_logger.info(
                    "Schedule task %s is already claimed by another execution", task_id
                )
                return EventResponse.reschedule(watchdog_delay)
            self.handler_logger.exception("Schedule task start failed", exc_info=error)
            return EventResponse.reschedule()
        return None

    async def reschedule_after_failed_submit(self, task_id: str) -> None:
        """Restore a started task after runner submission failure."""
        try:
            await self.task_service.reschedule(task_id)
        except MPTError as error:
            self.handler_logger.exception("Schedule task reschedule failed", exc_info=error)

    def map_context_error(self, error: Exception) -> EventResponse:
        """Map context construction failures to schedule acceptance responses."""
        if isinstance(error, AuthenticationError):
            self.handler_logger.error("Schedule task authentication failed", exc_info=error)
            return EventResponse.cancel(reason="Authentication failed")
        if isinstance(error, NON_RECOVERABLE_CONTEXT_ERRORS):
            self.handler_logger.error(
                "Schedule context creation is not recoverable", exc_info=error
            )
            return EventResponse.cancel(reason="Non-recoverable context error")
        self.handler_logger.error("Schedule context creation failed", exc_info=error)
        return EventResponse.reschedule()
