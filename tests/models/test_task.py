import warnings

import pytest

from mpt_extension_sdk.models.task import (
    Task,
    TaskLog,
    TaskLogSeverity,
    TaskParameters,
    TaskStatus,
    UnknownTaskStatusWarning,
)


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


def test_parameters_without_limits():
    task = Task.from_payload({
        "id": "TSK-001",
        "status": "Processing",
        "parameters": {"extensionId": "EXT-7847-1229"},
    })  # act

    assert task.parameters.max_task_processing_seconds is None
    assert task.parameters.max_task_lifetime_seconds is None


@pytest.mark.parametrize("severity", ["debug", "Info", "WARNING", "Error", "failure"])
def test_task_log_severity_ignores_case(severity):
    task_log = TaskLog(message="Synchronizing", severity=severity)  # act

    assert task_log.severity == TaskLogSeverity(severity.capitalize())


@pytest.mark.parametrize(
    ("status", "is_final"),
    [
        ("Completed", True),
        ("Failed", True),
        ("Processing", False),
        ("Queued", False),
        ("Rescheduled", False),
        ("Waiting", False),
    ],
)
@pytest.mark.filterwarnings("ignore::mpt_extension_sdk.models.task.UnknownTaskStatusWarning")
def test_task_status_helpers(status, is_final):
    task = Task(id="TASK-1", status=status)  # act

    assert task.is_final is is_final


def test_task_status_parses_known_status_as_enum():
    task = Task(id="TASK-1", status="Completed")  # act

    assert task.status == TaskStatus.COMPLETED


@pytest.mark.filterwarnings("ignore::mpt_extension_sdk.models.task.UnknownTaskStatusWarning")
def test_task_status_keeps_unknown_as_string():
    task = Task(id="TASK-1", status="Waiting")  # act

    assert task.status == "Waiting"
    assert task.is_final is False


def test_task_warns_on_unknown_status():
    with pytest.warns(UnknownTaskStatusWarning, match="TASK-1"):
        Task(id="TASK-1", status="Waiting")  # act


def test_task_does_not_warn_on_known_status():
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownTaskStatusWarning)

        Task(id="TASK-1", status="Completed")  # act


@pytest.fixture
def task_parameters():
    return TaskParameters.from_payload({
        "extensionId": "EXT-7847-1229",
        "maxTaskProcessingSeconds": 3600,
        "maxTaskLifetimeSeconds": 43200,
        "instanceId": "EXI-1",
    })


def test_parameters_keep_free_form_keys(task_parameters):
    result = task_parameters.to_dict()

    assert result == {
        "extensionId": "EXT-7847-1229",
        "maxTaskProcessingSeconds": 3600,
        "maxTaskLifetimeSeconds": 43200,
        "instanceId": "EXI-1",
    }


@pytest.mark.parametrize(
    ("name", "param_value"),
    [("syncCursor", "AGR-0001"), ("instanceId", "EXI-2")],
)
def test_parameters_with_parameter(task_parameters, name, param_value):
    result = task_parameters.with_parameter(name, param_value)

    assert result.to_dict() == {**task_parameters.to_dict(), name: param_value}


@pytest.mark.parametrize("name", ["instanceId", "missing"])
def test_parameters_without_parameter(task_parameters, name):
    expected = task_parameters.to_dict()
    expected.pop(name, None)

    result = task_parameters.without_parameter(name)

    assert result.to_dict() == expected


def test_parameters_keep_null_free_form_keys():
    task_parameters = TaskParameters.from_payload({"extensionId": "EXT-1", "syncCursor": None})

    result = task_parameters.with_parameter("instanceId", "EXI-1")

    assert result.to_dict() == {
        "extensionId": "EXT-1",
        "syncCursor": None,
        "instanceId": "EXI-1",
    }


def test_parameters_omit_absent_reserved_keys():
    task_parameters = TaskParameters.from_payload({"syncCursor": None})

    result = task_parameters.to_dict()

    assert result == {"syncCursor": None}


RESERVED_PARAMETERS = (
    "extensionId",
    "maxTaskProcessingSeconds",
    "maxTaskLifetimeSeconds",
    "extension_id",
    "max_task_processing_seconds",
    "max_task_lifetime_seconds",
)


@pytest.mark.parametrize("name", RESERVED_PARAMETERS)
def test_parameters_refuse_to_set_reserved(task_parameters, name):
    with pytest.raises(ValueError, match="reserved"):
        task_parameters.with_parameter(name, "changed")  # act


@pytest.mark.parametrize("name", RESERVED_PARAMETERS)
def test_parameters_refuse_to_remove_reserved(task_parameters, name):
    with pytest.raises(ValueError, match="reserved"):
        task_parameters.without_parameter(name)  # act
