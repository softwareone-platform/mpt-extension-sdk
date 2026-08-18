from mpt_extension_sdk.models.task import Task


def test_task_reads_published_limits():
    task = Task.from_payload({
        "id": "TSK-001",
        "status": "Processing",
        "parameters": {
            "extensionId": "EXT-7847-1229",
            "maxTaskProcessingSeconds": 3600,
            "maxTaskLifetimeSeconds": 43200,
        },
    })  # act

    assert task.parameters.max_task_processing_seconds == 3600
    assert task.parameters.max_task_lifetime_seconds == 43200


def test_task_without_parameters_has_no_limits():
    task = Task.from_payload({"id": "TSK-001", "status": "Processing"})  # act

    assert task.parameters is None


def test_task_parameters_without_limits():
    task = Task.from_payload({
        "id": "TSK-001",
        "status": "Processing",
        "parameters": {"extensionId": "EXT-7847-1229"},
    })  # act

    assert task.parameters.max_task_processing_seconds is None
    assert task.parameters.max_task_lifetime_seconds is None
