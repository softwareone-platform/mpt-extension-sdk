import pytest
from ninja import NinjaAPI

from mpt_extension_sdk.core.events.registry import EventsRegistry
from mpt_extension_sdk.runtime.events.utils import setup_contexts
from mpt_extension_sdk.runtime.utils import (
    get_api_url,
    get_events_registry,
    get_extension,
    get_extension_app_config,
    get_extension_app_config_name,
    get_extension_variables,
    get_urlpatterns,
)


def test_get_extension_app_config_name(mock_app_group_name):
    app_config_name = get_extension_app_config_name(group=mock_app_group_name)
    assert app_config_name == "mpt_extension_sdk.runtime.djapp.apps.ExtensionConfig"


def test_get_extension_appconfig(mock_app_group_name):
    appconfig = get_extension_app_config(group=mock_app_group_name)
    assert appconfig.name == "mpt_extension_sdk"
    assert appconfig.label == "mpt_extension_sdk"


def test_get_extension(mock_app_group_name):
    extension = get_extension(group=mock_app_group_name)
    assert extension is not None
    assert isinstance(extension.api, NinjaAPI)
    assert isinstance(extension.events, EventsRegistry)


def test_get_events_registry(mock_app_group_name):
    events_registry = get_events_registry(group=mock_app_group_name)
    assert events_registry.listeners is not None
    assert isinstance(events_registry.listeners, dict)


def test_get_extension_variables_valid(
    monkeypatch,
    mock_valid_env_values,
    mock_ext_expected_environment_values,
    mock_json_ext_variables,
):
    for key, value in mock_valid_env_values.items():
        monkeypatch.setenv(key, value)

    extension_variables = get_extension_variables(mock_json_ext_variables)

    assert mock_ext_expected_environment_values.items() <= extension_variables.items()


def test_get_extension_variables_json_error(
    monkeypatch, mock_invalid_env_values, mock_json_ext_variables
):
    for key, value in mock_invalid_env_values.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(Exception) as e:
        get_extension_variables(mock_json_ext_variables)

    assert "Variable EXT_PRODUCT_SEGMENT not well formatted" in str(e.value)


def test_setup_contexts(mpt_client, order_factory):
    orders = [order_factory()]
    contexts = setup_contexts(mpt_client, orders)
    assert len(contexts) == 1
    assert contexts[0].order == orders[0]


def test_get_api_urls_no_extension():
    extension = None
    urlpatterns = get_urlpatterns(extension)
    assert len(urlpatterns) == 1


def test_get_api_url_with_no_api_url(
    mocker,
    mock_app_group_name,
):
    extension = get_extension(group=mock_app_group_name)
    mocker.patch(
        "mpt_extension_sdk.runtime.utils.get_api_url",
        return_value=None,
    )
    urlpatterns = get_urlpatterns(extension)
    assert len(urlpatterns) == 1


def test_get_api_url_no_extension():
    extension = None
    api_url = get_api_url(extension)
    assert api_url is None
