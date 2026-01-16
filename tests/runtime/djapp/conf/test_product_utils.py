from mpt_extension_sdk.runtime.djapp.conf.product_utils import (
    extract_product_ids,
    get_for_product,
)


def test_extract_product_ids_splits_comma_separated_string():
    product_ids = "PRD-1234-1,PRD-1234-2"

    result = extract_product_ids(product_ids)

    assert result == ["PRD-1234-1", "PRD-1234-2"]


def test_get_for_product_returns_value_for_product(settings):
    settings.EXTENSION_CONFIG = {
        "AIRTABLE_BASES": {"PRD-1234-1": "base-id-1", "PRD-1234-2": "base-id-2"}
    }

    result = get_for_product(settings, "AIRTABLE_BASES", "PRD-1234-1")

    assert result == "base-id-1"
