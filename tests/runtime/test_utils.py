import pytest
from ninja import NinjaAPI

from mpt_extension_sdk.core.events.registry import EventsRegistry
from mpt_extension_sdk.runtime import utils
from mpt_extension_sdk.runtime.utils import (
    get_api_url,
    get_events_registry,
    get_extension,
    get_extension_app_config,
    get_extension_app_config_name,
    get_extension_variables,
    get_initializer_function,
    get_urlpatterns,
)


def test_get_extension_app_config_name(mock_app_group_name):
    result = get_extension_app_config_name(group=mock_app_group_name)

    assert result == "mpt_extension_sdk.runtime.djapp.apps.ExtensionConfig"


def test_get_extension_appconfig(mock_app_group_name):
    result = get_extension_app_config(group=mock_app_group_name)

    assert result.name == "mpt_extension_sdk"
    assert result.label == "mpt_extension_sdk"


def test_get_extension(mock_app_group_name):
    result = get_extension(group=mock_app_group_name)

    assert result is not None
    assert isinstance(result.api, NinjaAPI)
    assert isinstance(result.events, EventsRegistry)


def test_get_events_registry(mock_app_group_name):
    result = get_events_registry(group=mock_app_group_name)

    assert result.listeners is not None
    assert isinstance(result.listeners, dict)


def test_get_extension_variables_valid(
    monkeypatch,
    mock_valid_env_values,
    mock_ext_expected_environment_values,
    mock_json_ext_variables,
):
    for key, value in mock_valid_env_values.items():
        monkeypatch.setenv(key, value)

    result = get_extension_variables(mock_json_ext_variables)

    assert mock_ext_expected_environment_values.items() <= result.items()


def test_get_extension_variables_json_error(
    monkeypatch, mock_invalid_env_values, mock_json_ext_variables
):
    for key, value in mock_invalid_env_values.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(Exception) as e:
        get_extension_variables(mock_json_ext_variables)

    assert "Variable EXT_PRODUCT_SEGMENT not well formatted" in str(e.value)


def test_get_api_urls_no_extension():
    extension = None

    result = get_urlpatterns(extension)

    assert len(result) == 1


def test_get_api_url_with_no_api_url(mocker, mock_app_group_name):
    extension = get_extension(group=mock_app_group_name)
    mocker.patch("mpt_extension_sdk.runtime.utils.get_api_url", autospec=True, return_value=None)

    result = get_urlpatterns(extension)

    assert len(result) == 1


def test_get_api_url_no_extension():
    extension = None

    result = get_api_url(extension)

    assert result is None


def test_get_initializer_function(monkeypatch):
    monkeypatch.setenv("MPT_INITIALIZER", "tests.runtime.initializer.initialize_test")

    result = get_initializer_function()

    assert result is not None
    assert isinstance(result, str)
    assert result == "tests.runtime.initializer.initialize_test"


def test_initialize_extension_calls_initializer(mocker):
    mock_initializer = mocker.Mock(autospec=True)
    mock_import_string = mocker.patch(
        "mpt_extension_sdk.runtime.utils.import_string",
        return_value=mock_initializer,
        autospec=True,
    )
    mocker.patch(
        "mpt_extension_sdk.runtime.utils.get_initializer_function",
        return_value="dummy.path.to.initializer",
        autospec=True,
    )
    options = {"test_name": "test_value"}
    group = "test_group"
    name = "test_name"

    utils.initialize_extension(options, group=group, name=name)  # act

    mock_import_string.assert_called_once_with("dummy.path.to.initializer")
    mock_initializer.assert_called_once_with(options, group=group, name=name)
