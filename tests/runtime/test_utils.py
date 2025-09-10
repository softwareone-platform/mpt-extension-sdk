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
    """Test that the app config name is correctly constructed from the app group name."""
    app_config_name = get_extension_app_config_name(group=mock_app_group_name)
    assert app_config_name == "mpt_extension_sdk.runtime.djapp.apps.ExtensionConfig"


def test_get_extension_appconfig(mock_app_group_name):
    """Test that the app config is correctly retrieved from the app group name."""
    appconfig = get_extension_app_config(group=mock_app_group_name)
    assert appconfig.name == "mpt_extension_sdk"
    assert appconfig.label == "mpt_extension_sdk"


def test_get_extension(mock_app_group_name):
    """Test that the extension is correctly retrieved from the app group name."""
    extension = get_extension(group=mock_app_group_name)
    assert extension is not None
    assert isinstance(extension.api, NinjaAPI)
    assert isinstance(extension.events, EventsRegistry)


def test_get_events_registry(mock_app_group_name):
    """Test that the events registry is correctly retrieved from the extension."""
    events_registry = get_events_registry(group=mock_app_group_name)
    assert events_registry.listeners is not None
    assert isinstance(events_registry.listeners, dict)


def test_get_extension_variables_valid(
    monkeypatch,
    mock_valid_env_values,
    mock_ext_expected_environment_values,
    mock_json_ext_variables,
):
    """Test that the extension variables are correctly retrieved from the environment."""
    for key, value in mock_valid_env_values.items():
        monkeypatch.setenv(key, value)

    extension_variables = get_extension_variables(mock_json_ext_variables)

    assert mock_ext_expected_environment_values.items() <= extension_variables.items()


def test_get_extension_variables_json_error(
    monkeypatch, mock_invalid_env_values, mock_json_ext_variables
):
    """Test that an error is raised when the JSON environment variables are not well formatted."""
    for key, value in mock_invalid_env_values.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(Exception) as e:
        get_extension_variables(mock_json_ext_variables)

    assert "Variable EXT_PRODUCT_SEGMENT not well formatted" in str(e.value)


def test_get_api_urls_no_extension():
    """Test get_api_url when no extension is provided."""
    extension = None
    urlpatterns = get_urlpatterns(extension)
    assert len(urlpatterns) == 1


def test_get_api_url_with_no_api_url(
    mocker,
    mock_app_group_name,
):
    """Test get_api_url when no API URL is set in the extension."""
    extension = get_extension(group=mock_app_group_name)
    mocker.patch(
        "mpt_extension_sdk.runtime.utils.get_api_url",
        return_value=None,
    )
    urlpatterns = get_urlpatterns(extension)
    assert len(urlpatterns) == 1


def test_get_api_url_no_extension():
    """Test that get_api_url returns None when no extension is provided."""
    extension = None
    api_url = get_api_url(extension)
    assert api_url is None


def test_get_initializer_function(monkeypatch):
    """Test that the initializer function is correctly retrieved."""
    monkeypatch.setenv("MPT_INITIALIZER", "tests.runtime.initializer.initialize_test")

    func = get_initializer_function()
    assert func is not None
    assert isinstance(func, str)
    assert func == "tests.runtime.initializer.initialize_test"


def test_initialize_extension_calls_initializer(mocker):
    """Test that initialize_extension imports and correctly calls the initializer function."""
    mock_initializer = mocker.Mock(autospec=True)

    mock_import_string = mocker.patch(
        "mpt_extension_sdk.runtime.utils.import_string", return_value=mock_initializer
    )

    mocker.patch(
        "mpt_extension_sdk.runtime.utils.get_initializer_function",
        return_value="dummy.path.to.initializer",
    )

    options = {"test_name": "test_value"}
    group = "test_group"
    name = "test_name"

    utils.initialize_extension(options, group=group, name=name)
    mock_import_string.assert_called_once_with("dummy.path.to.initializer")
    mock_initializer.assert_called_once_with(options, group=group, name=name)
