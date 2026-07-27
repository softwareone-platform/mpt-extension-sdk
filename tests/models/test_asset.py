from decimal import Decimal

import pytest

from mpt_extension_sdk.models.asset import (
    Asset,
    AssetSimple,
    AssetStatus,
    UnknownAssetStatusWarning,
)


@pytest.fixture
def asset_payload():
    return {"id": "AST-1234-1234", "name": "Asset"}


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("New", AssetStatus.NEW),
        ("Draft", AssetStatus.DRAFT),
        ("Active", AssetStatus.ACTIVE),
        ("Terminated", AssetStatus.TERMINATED),
        ("active", AssetStatus.ACTIVE),
    ],
)
def test_asset_parses_known_status_into_enum(asset_payload, status, expected):
    result = AssetSimple.model_validate(asset_payload | {"status": status})

    assert result.status is expected
    assert result.model_dump(mode="json")["status"] == expected.value


def test_asset_keeps_unknown_status_as_string(asset_payload):
    with pytest.warns(UnknownAssetStatusWarning, match="AST-1234-1234"):
        result = AssetSimple.model_validate(asset_payload | {"status": "UnknownStatus"})

    assert result.status == "UnknownStatus"
    assert not isinstance(result.status, AssetStatus)
    assert result.model_dump(mode="json")["status"] == "UnknownStatus"


def test_asset_status_rejects_non_string_lookup():
    with pytest.raises(ValueError, match="not a valid AssetStatus"):
        AssetStatus(0)


def test_asset_accepts_external_ids_payload_alias():
    payload = {
        "id": "AST-1",
        "name": "Asset 1",
        "status": "active",
        "externalIds": {"vendor": "VEN-1"},
        "price": {"currency": "EUR", "unitPP": Decimal(0), "unitSP": Decimal(0)},
    }
    asset = Asset.from_payload(payload)

    result = asset.external_id.vendor

    assert result == "VEN-1"


def test_asset_line_accepts_old_qty_alias():
    payload = {
        "id": "AST-1",
        "name": "Asset 1",
        "status": "active",
        "externalIds": {"vendor": "VEN-1"},
        "price": {"currency": "EUR", "unitPP": Decimal(0), "unitSP": Decimal(0)},
        "lines": [
            {
                "id": "LINE-1",
                "oldQuantity": 1,
                "quantity": 2,
                "price": {"currency": "EUR", "unitPP": Decimal(0), "unitSP": Decimal(0)},
            }
        ],
    }
    asset = Asset.from_payload(payload)

    result = asset.lines[0].old_quantity

    assert result == 1
