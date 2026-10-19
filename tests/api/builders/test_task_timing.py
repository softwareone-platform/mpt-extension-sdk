import datetime as dt

import pytest
from freezegun import freeze_time

from mpt_extension_sdk.api.builders.task_timing import (
    FALLBACK_MAX_TASK_PROCESSING,
    TASK_TIMEOUT_SAFETY_MARGIN,
    delivery_latency_seconds,
    get_execution_deadline,
)


def test_delivery_latency_between_timestamps():
    enqueued_at = dt.datetime(2026, 8, 11, 17, 4, tzinfo=dt.UTC)

    result = delivery_latency_seconds(enqueued_at, enqueued_at + dt.timedelta(milliseconds=514))

    assert result == pytest.approx(0.514)


@freeze_time("2024-06-01")
def test_execution_deadline_uses_processing(task_factory):
    task = task_factory("Queued")

    result = get_execution_deadline(task)

    assert result == 7140


@freeze_time("2024-06-01")
def test_deadline_subtracts_elapsed_processing(task_factory):
    task = task_factory("Processing", created_seconds_ago=7100, started_seconds_ago=7100)

    result = get_execution_deadline(task)

    assert result == 40


@freeze_time("2024-06-01")
def test_deadline_uses_published_processing(task_factory, mocker):
    logger = mocker.patch("mpt_extension_sdk.api.builders.task_timing.logger")
    task = task_factory("Queued", task_parameters={"maxTaskProcessingSeconds": 3600})

    result = get_execution_deadline(task)

    assert result == 3540
    reported_fields = [call.args[1] for call in logger.error.call_args_list]
    assert reported_fields == ["maxTaskLifetimeSeconds"]


@freeze_time("2024-06-01")
def test_deadline_uses_published_lifetime(task_factory, mocker):
    logger = mocker.patch("mpt_extension_sdk.api.builders.task_timing.logger")
    task = task_factory(
        "Processing", created_seconds_ago=42000, task_parameters={"maxTaskLifetimeSeconds": 43200}
    )

    result = get_execution_deadline(task)

    assert result == 1140
    reported_fields = [call.args[1] for call in logger.error.call_args_list]
    assert reported_fields == ["maxTaskProcessingSeconds"]


@freeze_time("2024-06-01")
def test_deadline_reports_error_on_missing_limits(task_factory, mocker):
    logger = mocker.patch("mpt_extension_sdk.api.builders.task_timing.logger")
    task = task_factory("Queued")

    result = get_execution_deadline(task)

    assert result == FALLBACK_MAX_TASK_PROCESSING - TASK_TIMEOUT_SAFETY_MARGIN
    reported_fields = [call.args[1] for call in logger.error.call_args_list]
    assert reported_fields == ["maxTaskProcessingSeconds", "maxTaskLifetimeSeconds"]


@freeze_time("2024-06-01")
def test_execution_deadline_capped_by_lifespan(task_factory):
    task = task_factory("Processing", created_seconds_ago=84000)

    result = get_execution_deadline(task)

    assert result == 2340
