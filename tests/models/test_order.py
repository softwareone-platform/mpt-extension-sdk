from decimal import Decimal

import pytest

from mpt_extension_sdk.models.account import Account, SellerAccount
from mpt_extension_sdk.models.agreement import Agreement
from mpt_extension_sdk.models.authorization import Authorization
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.licensee import Licensee
from mpt_extension_sdk.models.order import Order, OrderLine
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
            status="Open",
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
