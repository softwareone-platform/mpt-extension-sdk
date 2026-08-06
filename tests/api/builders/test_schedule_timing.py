import pytest
from freezegun import freeze_time

from mpt_extension_sdk.api.builders.schedule_timing import (
    MAX_WATCHDOG_DELAY_SECONDS,
    MIN_WATCHDOG_DELAY_SECONDS,
    get_execution_deadline,
    watchdog_delay_seconds,
)


@pytest.mark.parametrize(
    ("started_seconds_ago", "expected_delay"),
    [
        (0, MIN_WATCHDOG_DELAY_SECONDS),
        (600, 600),
        (7200, MAX_WATCHDOG_DELAY_SECONDS),
    ],
)
@freeze_time("2024-06-01")
def test_watchdog_delay_backoff(task_factory, started_seconds_ago, expected_delay):
    task = task_factory("Processing", started_seconds_ago=started_seconds_ago)

    result = watchdog_delay_seconds(task)

    assert result == expected_delay


@freeze_time("2024-06-01")
def test_watchdog_delay_capped_by_retention(task_factory):
    task = task_factory("Processing", created_seconds_ago=604700, started_seconds_ago=3600)

    result = watchdog_delay_seconds(task)

    assert result == 60


@freeze_time("2024-06-01")
def test_execution_deadline_uses_processing(task_factory):
    task = task_factory("Queued")

    result = get_execution_deadline(task)

    assert result == 7140


@freeze_time("2024-06-01")
def test_execution_deadline_capped_by_lifespan(task_factory):
    task = task_factory("Processing", created_seconds_ago=84000)

    result = get_execution_deadline(task)

    assert result == 2340
