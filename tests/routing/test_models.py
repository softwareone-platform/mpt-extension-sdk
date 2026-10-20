import pytest

from mpt_extension_sdk.routing import TaskTimeouts


@pytest.mark.parametrize(
    ("max_task_lifespan", "max_task_processing"),
    [(7200, None), (None, 3600), (7200, 3600)],
)
def test_task_timeouts_accepts_declared_limit(max_task_lifespan, max_task_processing):
    result = TaskTimeouts(
        max_task_lifespan=max_task_lifespan, max_task_processing=max_task_processing
    )

    assert result.max_task_lifespan == max_task_lifespan
    assert result.max_task_processing == max_task_processing


def test_task_timeouts_rejects_no_limit():
    with pytest.raises(ValueError, match="must declare max_task_lifespan, max_task_processing"):
        TaskTimeouts()
