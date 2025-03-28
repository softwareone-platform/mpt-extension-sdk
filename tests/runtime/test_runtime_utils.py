import pytest
from ninja import NinjaAPI

from mpt_extension_sdk.core.events.registry import EventsRegistry
from mpt_extension_sdk.runtime.events.utils import setup_contexts
from mpt_extension_sdk.runtime.utils import (
    get_events_registry,
    get_extension,
    get_extension_app_config,
    get_extension_app_config_name,
    get_extension_variables,
)


def test_get_extension_app_config_name():
    app_config_name = get_extension_app_config_name()
    assert app_config_name == "mpt_extension_sdk.runtime.djapp.apps.ExtensionConfig"


def test_get_extension_appconfig():
    appconfig = get_extension_app_config()
    assert appconfig.name == "mpt_extension_sdk"
    assert appconfig.label == "mpt_extension_sdk"


def test_get_extension():
    extension = get_extension()
    assert extension is not None
    assert isinstance(extension.api, NinjaAPI)
    assert isinstance(extension.events, EventsRegistry)


def test_get_events_registry():
    events_registry = get_events_registry()
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
