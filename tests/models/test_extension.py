import warnings

import pytest

from mpt_extension_sdk.models.extension import (
    Extension,
    ExtensionStatusEnum,
    UnknownExtensionStatusWarning,
)


@pytest.fixture
def extension_payload():
    return {
        "id": "EXT-1234-1234",
        "name": "Extension",
        "vendor": {"id": "ACC-1", "name": "Vendor"},
    }


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Deleted", ExtensionStatusEnum.DELETED),
        ("Draft", ExtensionStatusEnum.DRAFT),
        ("Private", ExtensionStatusEnum.PRIVATE),
        ("Public", ExtensionStatusEnum.PUBLIC),
        ("public", ExtensionStatusEnum.PUBLIC),
    ],
)
def test_extension_parses_known_status(extension_payload, status, expected):
    result = Extension.model_validate(extension_payload | {"status": status})

    assert result.status is expected
    assert result.model_dump(mode="json")["status"] == expected.value


def test_extension_keeps_unknown_status(extension_payload):
    with pytest.warns(UnknownExtensionStatusWarning, match="EXT-1234-1234"):
        result = Extension.model_validate(extension_payload | {"status": "UnknownStatus"})

    assert result.status == "UnknownStatus"
    assert not isinstance(result.status, ExtensionStatusEnum)


def test_extension_defaults_missing_status(extension_payload):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownExtensionStatusWarning)

        result = Extension.model_validate(extension_payload)

    assert result.status is None


def test_extension_rejects_non_string():
    with pytest.raises(ValueError, match="not a valid ExtensionStatusEnum"):
        ExtensionStatusEnum(0)
