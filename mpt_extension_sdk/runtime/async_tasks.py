import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from mpt_extension_sdk.errors.runtime import AsyncTasksRunnerError
from mpt_extension_sdk.runtime.task_transitions import SafeTaskTransitions
from mpt_extension_sdk.services.mpt_api_service.task import TaskService

logger = logging.getLogger(__name__)

AsyncTaskHandler = Callable[[], Awaitable[None]]
PROCESSING_TIMEOUT_REASON = "Processing timeout exceeded"
SHUTDOWN_INTERRUPTION_REASON = "Interrupted by instance shutdown"


@dataclass(frozen=True)
class TaskExecution:
    """Task execution request accepted by the async runner."""

    task_id: str
    task_callback: AsyncTaskHandler
    task_service: TaskService
    handler_logger: logging.Logger
    deadline_seconds: float


@dataclass(frozen=True)
class RunningTask:
    """Task execution state kept for shutdown finalization."""

    task: asyncio.Task[None]
    transitions: SafeTaskTransitions


class AsyncTaskRunner:
    """Run SDK-managed tasks outside the HTTP request lifecycle."""

    def __init__(self) -> None:
        """Initialize an empty local task registry."""
        self._reserved: dict[str, asyncio.Task[object] | None] = {}
        self._running: dict[str, RunningTask] = {}
        self._shutting_down = False

    def is_running(self, task_id: str) -> bool:
        """Return whether this process is already executing a task."""
        return task_id in self._running

    @contextmanager
    def reserve(self, task_id: str) -> Iterator[bool]:
        """Atomically reserve a task while it is being accepted."""
        if self._shutting_down or task_id in self._reserved or self.is_running(task_id):
            yield False
            return

        self._reserved[task_id] = self._get_current_task()
        try:
            yield True
        finally:
            self._reserved.pop(task_id, None)

    def submit(self, *, execution: TaskExecution) -> bool:
        """Submit an asynchronous task if it is not already running locally.

        Returns:
            True when a new execution was submitted, otherwise False.
        """
        task_id = execution.task_id
        if self._shutting_down or self.is_running(task_id):
            return False

        if task_id in self._reserved and self._reserved[task_id] is not self._get_current_task():
            return False

        if task_id not in self._reserved:
            self._reserved[task_id] = self._get_current_task()

        try:
            background_task = asyncio.create_task(
                self._run_task(execution), name=f"mpt-task-{task_id}"
            )
        except RuntimeError as error:
            self._reserved.pop(task_id, None)
            raise AsyncTasksRunnerError(
                f"Failed to submit task: {error}", task_id=task_id
            ) from None

        self._running[task_id] = RunningTask(
            task=background_task,
            transitions=SafeTaskTransitions(execution.task_service, execution.handler_logger),
        )
        self._reserved.pop(task_id, None)
        return True

    async def shutdown(self) -> None:
        """Cancel local executions and fail interrupted platform tasks."""
        self._shutting_down = True
        self._reserved.clear()
        running_tasks = dict(self._running)
        cancelled_tasks = [entry.task for entry in running_tasks.values()]
        for cancelled_task in cancelled_tasks:
            cancelled_task.cancel()
        await asyncio.gather(*cancelled_tasks, return_exceptions=True)
        await asyncio.gather(
            *(
                entry.transitions.fail(task_id, reason=SHUTDOWN_INTERRUPTION_REASON)
                for task_id, entry in running_tasks.items()
            )
        )

    async def _run_task(self, execution: TaskExecution) -> None:  # noqa: WPS213
        transitions = SafeTaskTransitions(execution.task_service, execution.handler_logger)
        try:
            await asyncio.wait_for(
                execution.task_callback(),
                timeout=execution.deadline_seconds,
            )
        except TimeoutError:
            execution.handler_logger.exception(
                "Async task %s exceeded its processing timeout", execution.task_id
            )
            await transitions.fail(execution.task_id, reason=PROCESSING_TIMEOUT_REASON)
        except asyncio.CancelledError:
            # shutdown() fails the interrupted platform tasks after cancellation.
            execution.handler_logger.warning(
                "Async task %s interrupted by runtime shutdown", execution.task_id
            )
            raise
        except Exception as error:
            await transitions.transition_on_error(execution.task_id, error)
        else:
            execution.handler_logger.info("Async task %s completed successfully", execution.task_id)
            await transitions.complete(execution.task_id)
        finally:
            self._running.pop(execution.task_id, None)

    def _get_current_task(self) -> asyncio.Task[object] | None:
        """Return the current asyncio task when running inside an event loop."""
        try:
            return asyncio.current_task()
        except RuntimeError:
            return None
