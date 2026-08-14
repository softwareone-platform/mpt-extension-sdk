import datetime as dt

import pytest
from freezegun import freeze_time

from mpt_extension_sdk.api.builders.schedule_timing import (
    MAX_WATCHDOG_DELAY_SECONDS,
    MIN_WATCHDOG_DELAY_SECONDS,
    delivery_latency_seconds,
    get_execution_deadline,
    watchdog_delay_seconds,
)


@pytest.fixture
def enqueued_at():
    def factory(seconds_ago=0):
        return dt.datetime.now(dt.UTC) - dt.timedelta(seconds=seconds_ago)

    return factory


@pytest.mark.parametrize(
    ("started_seconds_ago", "expected_delay"),
    [
        (0, MIN_WATCHDOG_DELAY_SECONDS),
        (600, 600),
        (7200, MAX_WATCHDOG_DELAY_SECONDS),
    ],
)
@freeze_time("2024-06-01")
def test_watchdog_delay_backoff(task_factory, enqueued_at, started_seconds_ago, expected_delay):
    task = task_factory("Processing", started_seconds_ago=started_seconds_ago)

    result = watchdog_delay_seconds(task, enqueued_at=enqueued_at())

    assert result == expected_delay


@freeze_time("2024-06-01")
def test_watchdog_delay_capped_by_retention(task_factory, enqueued_at):
    task = task_factory("Processing", started_seconds_ago=3600)

    result = watchdog_delay_seconds(task, enqueued_at=enqueued_at(604700))

    assert result == 40


@freeze_time("2024-06-01")
def test_watchdog_delay_floors_near_expiry(task_factory, enqueued_at):
    task = task_factory("Processing", started_seconds_ago=3600)

    result = watchdog_delay_seconds(task, enqueued_at=enqueued_at(604770))

    assert result == 1


@freeze_time("2024-06-01")
def test_watchdog_retention_ignores_task_age(task_factory, enqueued_at):
    task = task_factory("Processing", created_seconds_ago=604700, started_seconds_ago=600)

    result = watchdog_delay_seconds(task, enqueued_at=enqueued_at(10))

    assert result == 600


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
def test_execution_deadline_capped_by_lifespan(task_factory):
    task = task_factory("Processing", created_seconds_ago=84000)

    result = get_execution_deadline(task)

    assert result == 2340
