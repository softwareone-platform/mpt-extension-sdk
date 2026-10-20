from collections.abc import Awaitable
from typing import cast

from mpt_extension_sdk.api.results import TaskResult
from mpt_extension_sdk.routing.types import APIRouteCallback
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskHandler
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


def build_deferred_callback(
    *,
    callback: APIRouteCallback,
    handler_arguments: dict[str, object],
    task_service: TaskService,
    task_id: str,
) -> AsyncTaskHandler:
    """Wrap a deferred handler so a returned TaskResult is stored on the platform Task.

    The runner completes the Task once the wrapped call returns, so the result is
    stored before the Task completes. Any other return value, None included, leaves
    the Task without a result.

    Args:
        callback: Deferrable API handler, always a coroutine function.
        handler_arguments: Resolved arguments the handler is called with.
        task_service: Marketplace Tasks service used to store the result.
        task_id: Unique identifier of the delivered platform task.

    Returns:
        The no-argument callable the async runner executes.
    """

    async def run_deferred_handler() -> None:  # noqa: WPS430
        outcome = await cast(Awaitable[object], callback(**handler_arguments))
        if isinstance(outcome, TaskResult):
            await task_service.set_result(task_id, outcome.uri)

    return run_deferred_handler
