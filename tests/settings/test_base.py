import pytest

from mpt_extension_sdk.settings.base import BaseSettings


@pytest.mark.parametrize(("env_value", "expected"), [("True", True), ("False", False)])
def test_base_settings_bool_env_vars(env_value, expected, monkeypatch):
    monkeypatch.setenv("TEST_ENV_BOOL", env_value)

    result = BaseSettings.bool_env("TEST_ENV_BOOL", default=False)

    assert result is expected
    assert isinstance(result, bool)


@pytest.mark.parametrize(("env_value", "expected"), [("123", 123), ("0", 0)])
def test_base_settings_int_env_vars(env_value, expected, monkeypatch):
    monkeypatch.setenv("TEST_ENV_INT", env_value)

    result = BaseSettings.int_env("TEST_ENV_INT", default=0)

    assert result == expected
    assert isinstance(result, int)


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        ("PRD-1", ["PRD-1"]),
        ("PRD-1, PRD-2", ["PRD-1", "PRD-2"]),
        ("PRD-1,PRD-2", ["PRD-1", "PRD-2"]),
        ("PRD-1, ,PRD-2", ["PRD-1", "PRD-2"]),
        ("", []),
    ],
)
def test_base_settings_list_env_vars(env_value, expected, monkeypatch):
    monkeypatch.setenv("TEST_ENV_LIST", env_value)

    result = BaseSettings.list_env("TEST_ENV_LIST")

    assert result == expected
    assert isinstance(result, list)


def test_base_settings_list_env_vars_unset(monkeypatch):
    monkeypatch.delenv("TEST_ENV_LIST", raising=False)

    result = BaseSettings.list_env("TEST_ENV_LIST")

    assert result == []
    assert isinstance(result, list)
