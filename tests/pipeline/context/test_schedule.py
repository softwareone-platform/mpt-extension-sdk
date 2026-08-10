from mpt_api_client.exceptions import MPTError

from mpt_extension_sdk.pipeline.context.schedule import ScheduleTaskHandle


async def test_schedule_task_reports_progress(task_service):
    task = ScheduleTaskHandle(id="TSK-1", task_service=task_service)

    await task.progress(0.5)  # act

    task_service.progress.assert_awaited_once_with("TSK-1", 0.5)


async def test_schedule_task_ignores_progress_errors(mocker, task_service):
    task_service.progress.side_effect = MPTError("MPT unavailable")
    task = ScheduleTaskHandle(id="TSK-1", task_service=task_service)
    logger = mocker.patch("mpt_extension_sdk.pipeline.context.schedule.logger")

    await task.progress(0.5)  # act

    logger.warning.assert_called_once()
