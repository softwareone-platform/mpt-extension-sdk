from decimal import Decimal

import pytest
from pydantic import ValidationError

from mpt_extension_sdk.models import OrderStatus
from mpt_extension_sdk.models.account import Account, SellerAccount
from mpt_extension_sdk.models.agreement import Agreement
from mpt_extension_sdk.models.authorization import Authorization
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.licensee import Licensee
from mpt_extension_sdk.models.order import (
    Order,
    OrderLine,
    OrderSimple,
    UnknownOrderStatusWarning,
)
from mpt_extension_sdk.models.parameter import ParameterBag
from mpt_extension_sdk.models.price import Price
from mpt_extension_sdk.models.product import ExternalIds as ProductExternalIds
from mpt_extension_sdk.models.product import Product, ProductItem


@pytest.fixture
def order_line_factory():
    def factory(line_id, *, old_quantity, quantity, vendor_sku):
        return OrderLine(
            id=line_id,
            old_quantity=old_quantity,
            quantity=quantity,
            item=ProductItem(
                id=f"ITEM-{line_id}",
                name=f"Item {line_id}",
                external_ids=ProductExternalIds(vendor=vendor_sku),
            ),
            price=Price(currency="EUR", unit_pp=Decimal(0), unit_sp=Decimal(0)),
        )

    return factory


@pytest.fixture
def full_order_factory(order_line_factory):
    def factory():
        return Order.model_construct(
            id="ORD-1",
            status=OrderStatus.PROCESSING,
            type="Order",
            agreement=Agreement.model_construct(
                id="AGR-1",
                name="Agreement 1",
                client=Account.model_construct(id="CLIENT-1", name="Client"),
                licensee=Licensee.model_construct(
                    id="LIC-1",
                    name="Licensee",
                    status="active",
                ),
                parameters=ParameterBag(),
                product=Product.model_construct(id="PROD-1", name="Product 1"),
                external_ids=ExternalIds(vendor="CUST-1"),
            ),
            authorization=Authorization.model_construct(id="AUTH-1", name="Auth", currency="EUR"),
            product=Product.model_construct(id="PROD-1", name="Product 1"),
            seller=SellerAccount.model_construct(id="SELL-1", name="Seller"),
            lines=[
                order_line_factory("1", old_quantity=5, quantity=3, vendor_sku="SKU-DOWN"),
                order_line_factory("2", old_quantity=2, quantity=4, vendor_sku="SKU-UP"),
                order_line_factory("3", old_quantity=0, quantity=1, vendor_sku="SKU-NEW"),
            ],
            parameters=ParameterBag(),
        )

    return factory


@pytest.fixture
def order_payload(full_order_factory):
    return full_order_factory().model_dump(by_alias=True)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Draft", OrderStatus.DRAFT),
        ("Quoted", OrderStatus.QUOTED),
        ("Processing", OrderStatus.PROCESSING),
        ("Querying", OrderStatus.QUERYING),
        ("Completed", OrderStatus.COMPLETED),
        ("Failed", OrderStatus.FAILED),
        ("Deleted", OrderStatus.DELETED),
        ("completed", OrderStatus.COMPLETED),
    ],
)
def test_order_parses_known_status_into_enum(order_payload, status, expected):
    result = Order.model_validate(order_payload | {"status": status})

    assert result.status is expected
    assert result.model_dump(mode="json")["status"] == expected.value


def test_order_keeps_unknown_status_as_string(order_payload):
    with pytest.warns(UnknownOrderStatusWarning, match="ORD-1"):
        result = Order.model_validate(order_payload | {"status": "UnknownStatus"})

    assert result.status == "UnknownStatus"
    assert not isinstance(result.status, OrderStatus)
    assert result.model_dump(mode="json")["status"] == "UnknownStatus"


def test_order_status_rejects_non_string_lookup():
    with pytest.raises(ValueError, match="not a valid OrderStatus"):
        OrderStatus(0)


def test_order_properties_expose_related_ids(full_order_factory):
    order = full_order_factory()

    result = (
        order.agreement_id,
        order.authorization_id,
        order.customer_id,
        order.product_id,
        order.seller_id,
    )

    assert result == ("AGR-1", "AUTH-1", "CUST-1", "PROD-1", "SELL-1")


def test_order_seller_id_returns_value(full_order_factory):
    order = full_order_factory()

    result = order.seller_id

    assert result == "SELL-1"


def test_order_line_groups(full_order_factory):
    order = full_order_factory()

    result = (
        [line.id for line in order.downsize_lines],
        [line.id for line in order.upsize_lines],
        [line.id for line in order.new_lines],
    )

    assert result == (["1"], ["2"], ["3"])


def test_get_line_by_sku_returns_matching_line(full_order_factory):
    order = full_order_factory()

    result = order.get_line_by_sku("SKU-UP")

    assert result.id == "2"


def test_get_line_by_sku_raises_when_missing(full_order_factory):
    source_order = full_order_factory()
    order = source_order.model_copy(update={"lines": source_order.lines[:1]})

    with pytest.raises(ValueError, match="No line found for SKU: missing"):
        order.get_line_by_sku("missing")


def test_order_defaults_parameter_bag(full_order_factory):
    order = full_order_factory()

    result = order.parameters

    assert isinstance(result, ParameterBag)


@pytest.fixture
def order_simple_payload(order_payload):
    agreement_reference = {"id": "AGR-1", "name": "Agreement", "status": "Draft"}
    return order_payload | {"agreement": agreement_reference}


def test_order_simple_accepts_agreement_reference(order_simple_payload):
    result = OrderSimple.model_validate(order_simple_payload)

    assert (result.agreement_id, result.agreement.name) == ("AGR-1", "Agreement")


def test_order_rejects_agreement_reference(order_simple_payload):
    with pytest.raises(ValidationError, match=r"agreement\.client"):
        Order.model_validate(order_simple_payload)


def test_order_is_an_order_simple(full_order_factory):
    order = full_order_factory()

    result = isinstance(order, OrderSimple)

    assert result is True


def test_order_simple_clears_errors(order_simple_payload):
    error = {"id": "ERR-1", "message": "Invalid"}
    order = OrderSimple.model_validate(
        order_simple_payload
        | {
            "error": error,
            "parameters": {"ordering": [{"externalId": "address", "error": error}]},
        }
    )

    result = order.without_errors()

    assert (result.error, result.parameters.get_ordering_parameter("address").error) == (
        None,
        None,
    )


def test_order_simple_sends_empty_error(order_simple_payload):
    payload = {key: field for key, field in order_simple_payload.items() if key != "error"}
    order = OrderSimple.model_validate(payload)

    result = order.without_errors()

    assert result.model_dump(exclude_unset=True)["error"] is None


def test_order_simple_keeps_parameters_unset(order_simple_payload):
    payload = {key: field for key, field in order_simple_payload.items() if key != "parameters"}
    order = OrderSimple.model_validate(payload)

    result = order.without_errors()

    assert "parameters" not in result.model_dump(exclude_unset=True)


def test_order_simple_sets_order_error(order_simple_payload):
    order = OrderSimple.model_validate(order_simple_payload)

    result = order.with_error({"id": "ERR-1", "message": "Invalid order"})

    assert result.model_dump(exclude_unset=True)["error"] == {
        "id": "ERR-1",
        "message": "Invalid order",
    }


def test_order_simple_sets_ordering_error(order_simple_payload):
    order = OrderSimple.model_validate(
        order_simple_payload | {"parameters": {"ordering": [{"externalId": "address"}]}}
    )

    result = order.with_ordering_error("address", {"id": "ERR-1", "message": "Invalid"})

    assert result.parameters.get_ordering_parameter("address").error == {
        "id": "ERR-1",
        "message": "Invalid",
    }


def test_order_simple_chains_errors(order_simple_payload):
    error = {"id": "ERR-1", "message": "Invalid"}
    order = OrderSimple.model_validate(
        order_simple_payload | {"parameters": {"ordering": [{"externalId": "address"}]}}
    )

    result = order.without_errors().with_ordering_error("address", error).with_error(error)

    assert (result.error, result.parameters.get_ordering_parameter("address").error) == (
        error,
        error,
    )
