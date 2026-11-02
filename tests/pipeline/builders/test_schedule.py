import datetime as dt

from mpt_extension_sdk.pipeline.builders import ScheduleContextBuilder
from mpt_extension_sdk.pipeline.context.schedule import ScheduleContext


async def test_build_schedule_context(logger, task_service, task_event, resources):
    builder = ScheduleContextBuilder(
        event=task_event,
        handler_logger=logger,
        schedule_id="agreements.sync",
        task_id="TSK-1",
        task_service=task_service,
    )

    result = await builder.build(resources)

    assert isinstance(result, ScheduleContext)
    assert (result.meta.schedule_id, result.meta.task_id, result.task.id) == (
        "agreements.sync",
        "TSK-1",
        "TSK-1",
    )
    assert (result.meta.event_id, result.meta.enqueue_time) == (
        task_event.id,
        dt.datetime(2026, 8, 11, 17, 4, tzinfo=dt.UTC),
    )
