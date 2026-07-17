import pytest

from mpt_extension_sdk.api.builders import dependencies


@pytest.fixture(autouse=True)
def clear_service_cache():
    dependencies._cached_tasks_service.cache_clear()
    yield
    dependencies._cached_tasks_service.cache_clear()


def test_get_tasks_service(mocker, runtime_settings):
    fake_api = mocker.Mock(spec=["tasks"])
    mock_mpt_api_service = mocker.patch(
        "mpt_extension_sdk.api.builders.dependencies.MPTAPIService", autospec=True
    )
    mock_mpt_api_service.from_config.return_value = fake_api

    result = dependencies.get_tasks_service(runtime_settings)

    assert result is fake_api.tasks
    mock_mpt_api_service.from_config.assert_called_once_with(
        base_url=runtime_settings.mpt_api_base_url, api_token=runtime_settings.ext_api_key
    )


def test_get_tasks_service_reuses_cached_client(mocker, runtime_settings):
    fake_api = mocker.Mock(spec=["tasks"])
    mock_mpt_api_service = mocker.patch(
        "mpt_extension_sdk.api.builders.dependencies.MPTAPIService", autospec=True
    )
    mock_mpt_api_service.from_config.return_value = fake_api
    first = dependencies.get_tasks_service(runtime_settings)

    second = dependencies.get_tasks_service(runtime_settings)  # act

    assert first is second
    mock_mpt_api_service.from_config.assert_called_once()
