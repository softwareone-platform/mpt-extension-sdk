import datetime as dt

import pytest

from mpt_extension_sdk.models.task import Task


@pytest.fixture
def task_factory():
    def factory(status, *, created_seconds_ago=0, started_seconds_ago=None):
        now = dt.datetime.now(dt.UTC)
        created_at = now - dt.timedelta(seconds=created_seconds_ago)
        audit = {"created": {"at": created_at.isoformat()}}
        if started_seconds_ago is not None:
            started_at = now - dt.timedelta(seconds=started_seconds_ago)
            audit["started"] = {"at": started_at.isoformat()}
        return Task(id="TSK-001", status=status, audit=audit)

    return factory
