from decimal import Decimal

from mpt_extension_sdk.models.asset import Asset


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
