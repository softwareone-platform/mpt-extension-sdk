import httpx
import pytest

from mpt_extension_sdk.runtime.bootstrap.registration import (
    RegistrationResult,
    register_instance,
    register_instance_on_reload,
)


@pytest.fixture
def registration_patches(mocker):
    return {
        "register_extension_instance": mocker.patch(
            "mpt_extension_sdk.runtime.bootstrap.registration.register_extension_instance",
            autospec=True,
        ),
        "save_identity": mocker.patch(
            "mpt_extension_sdk.runtime.bootstrap.registration.save_identity", autospec=True
        ),
        "load_identity": mocker.patch(
            "mpt_extension_sdk.runtime.bootstrap.registration.load_identity", autospec=True
        ),
    }


def test_register_instance_adds_channel(runtime_settings, registration_patches, mocker):
    register_extension_instance = registration_patches["register_extension_instance"]
    save_identity = registration_patches["save_identity"]
    registration_patches["load_identity"].return_value = {}
    register_extension_instance.return_value = {"id": "instance-1"}

    result = register_instance(runtime_settings)

    assert result == RegistrationResult(instance={"id": "instance-1"})
    register_extension_instance.assert_called_once_with(
        runtime_settings.base_url,
        runtime_settings.extension_id,
        runtime_settings.ext_api_key,
        mocker.ANY,
    )
    payload = register_extension_instance.call_args.args[3]
    assert payload["externalId"] == runtime_settings.external_id
    assert payload["version"] == runtime_settings.meta_config.version
    assert payload["meta"] == runtime_settings.meta_config.model_dump(
        exclude_none=True, by_alias=True
    )
    assert payload["channel"] == {}
    save_identity.assert_not_called()


def test_register_instance_reuses_identity(runtime_settings, registration_patches):
    register_extension_instance = registration_patches["register_extension_instance"]
    save_identity = registration_patches["save_identity"]
    registration_patches["load_identity"].return_value = {
        "mrok": {"extension": runtime_settings.extension_id.lower()}
    }
    register_extension_instance.return_value = {
        "channel": {"identity": {"mrok": {"extension": runtime_settings.extension_id}}}
    }

    result = register_instance(runtime_settings)

    assert result == RegistrationResult(
        instance={"channel": {"identity": {"mrok": {"extension": runtime_settings.extension_id}}}}
    )
    payload = register_extension_instance.call_args.args[3]
    assert "channel" not in payload
    save_identity.assert_called_once_with(
        runtime_settings.identity_file_path,
        {"mrok": {"extension": runtime_settings.extension_id}},
    )


def test_register_on_reload_registers_again(runtime_settings, mocker):
    register = mocker.patch(
        "mpt_extension_sdk.runtime.bootstrap.registration.register_instance", autospec=True
    )

    register_instance_on_reload(runtime_settings)  # act

    register.assert_called_once_with(runtime_settings)


def test_register_on_reload_survives_a_failure(runtime_settings, mocker):
    mocker.patch(
        "mpt_extension_sdk.runtime.bootstrap.registration.register_instance",
        autospec=True,
        side_effect=httpx.ConnectError("platform is down"),
    )

    result = register_instance_on_reload(runtime_settings)

    assert result is None
