import pytest

from mpt_extension_sdk.routing.paths import RoutePath


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/", "/"),
        ("/orders", "/orders"),
        ("/orders/", "/orders"),
        ("/orders/{order_id}", "/orders/{}"),
        ("/orders/{order_id:int}/", "/orders/{}"),
        ("/orders/{order_id}/lines/{line_id}", "/orders/{}/lines/{}"),
        ("/orders/{sync-all}", "/orders/{sync-all}"),
    ],
)
def test_normalize(path, expected):
    result = RoutePath.normalize(path)

    assert result == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/agreements/sync", []),
        ("/agreements/{agreement_id}", ["agreement_id"]),
        ("/agreements/{agreement_id:int}/lines/{line_id}", ["agreement_id", "line_id"]),
        ("/agreements/{sync-all}", []),
    ],
)
def test_parameter_names(path, expected):
    result = RoutePath.parameter_names(path)

    assert result == expected


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("/agreements/{agreement_id:unknown}", "declares an unknown path convertor"),
        ("/agreements/{agreement_id}/{agreement_id}", "Duplicated param name agreement_id"),
    ],
)
def test_parameter_names_rejects_invalid(path, message):
    with pytest.raises(ValueError, match=message):
        RoutePath.parameter_names(path)
