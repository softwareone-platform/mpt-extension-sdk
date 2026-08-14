import logging

from mpt_api_client.exceptions import MPTAPIError, MPTError, MPTHttpError

from mpt_extension_sdk.errors.mapping import map_exception_to_event_response
from mpt_extension_sdk.errors.pipeline import DeferError
from mpt_extension_sdk.services.mpt_api_service.task import TaskService

MISSING_TASK_STATUS_CODE = 404
TASK_CONFLICT_STATUS_CODE = 409
LIFECYCLE_REJECTION_STATUS_CODES = frozenset((MISSING_TASK_STATUS_CODE, TASK_CONFLICT_STATUS_CODE))


class SafeTaskTransitions:
    """Platform Task lifecycle transitions tolerant of finalized-task rejections.

    A transition rejected because the platform already finalized the task is not an
    error: the execution is simply late. The platform answers `409 Conflict` for that
    case, but also whenever the transition is not accepted from the task's current
    state, so a conflict is only tolerated after reading the task and confirming it
    is final. An unaccepted transition is logged at error level with the current
    status instead, since silence would hide it.

    No transition raises: they run as the terminal step of an execution, where the
    handler outcome has already been decided.
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
            await self._report_lifecycle_rejection(task_id, error)

    async def fail(self, task_id: str, reason: str | None = None) -> None:
        """Fail a task and ignore final-state lifecycle rejections."""
        try:
            await self.task_service.fail(task_id, reason=reason)
        except (MPTHttpError, MPTAPIError) as error:
            await self._report_lifecycle_rejection(task_id, error)

    async def reschedule(self, task_id: str) -> None:
        """Reschedule a task and ignore final-state lifecycle rejections."""
        try:
            await self.task_service.reschedule(task_id)
        except (MPTHttpError, MPTAPIError) as error:
            await self._report_lifecycle_rejection(task_id, error)

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

    async def _report_lifecycle_rejection(
        self, task_id: str, error: MPTHttpError | MPTAPIError
    ) -> None:
        """Report a lifecycle rejection, or re-raise when it is not one.

        Args:
            task_id: The platform task the transition was called on.
            error: The rejection raised by the Tasks API.

        Raises:
            MPTHttpError: If the failure is not a lifecycle rejection.
        """
        status_code = getattr(error, "status_code", None)
        if status_code not in LIFECYCLE_REJECTION_STATUS_CODES:
            raise error

        if status_code == MISSING_TASK_STATUS_CODE:
            self.handler_logger.warning(
                "Lifecycle transition for task %s was rejected: the task no longer exists",
                task_id,
            )
            return

        await self._report_conflict(task_id, error)

    async def _report_conflict(self, task_id: str, error: MPTHttpError | MPTAPIError) -> None:
        """Tell an already-final task from a transition the platform does not accept."""
        try:
            task = await self.task_service.get(task_id)
        except MPTError:
            self.handler_logger.exception(
                "Lifecycle transition for task %s was rejected with a conflict, and its current "
                "status could not be read: %s",
                task_id,
                error,
            )
            return

        if task.is_final:
            self.handler_logger.warning(
                "Lifecycle transition for task %s was rejected because the task is final (%s)",
                task_id,
                task.status,
            )
            return

        self.handler_logger.error(
            "Lifecycle transition for task %s was rejected: the platform does not accept it "
            "while the task is in %s: %s",
            task_id,
            task.status,
            error,
        )
