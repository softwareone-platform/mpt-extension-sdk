from mpt_extension_sdk.flows.context import (
    ORDER_TYPE_CHANGE,
    ORDER_TYPE_PURCHASE,
    ORDER_TYPE_TERMINATION,
    Context,
)


def test_context_get_order_id(
    order_factory,
):
    order = order_factory()
    context = Context(order)
    order_id = context.order_id
    assert order_id == order["id"]


def test_context_get_order_type(
    order_factory,
):
    order = order_factory()
    context = Context(order)
    order_type = context.order_type
    assert order_type == order["type"]


def test_context_get_product_id(
    order_factory,
):
    order = order_factory()
    context = Context(order)
    product_id = context.product_id
    assert product_id == order.get("product", {}).get("id", None)


def test_context_is_purchase_order(
    order_factory,
):
    order = order_factory()
    order["type"] = ORDER_TYPE_PURCHASE
    context = Context(order)
    is_purchase_order = context.is_purchase_order()
    assert is_purchase_order


def test_context_is_change_order(
    order_factory,
):
    order = order_factory()
    order["type"] = ORDER_TYPE_CHANGE
    context = Context(order)
    is_change_order = context.is_change_order()
    assert is_change_order


def test_context_is_termination_order(
    order_factory,
):
    order = order_factory()
    order["type"] = ORDER_TYPE_TERMINATION
    context = Context(order)
    is_termination_order = context.is_termination_order()
    assert is_termination_order


def test_from_context(
    order_factory,
):
    order = order_factory()
    context = Context(order)
    new_context = Context.from_context(context)
    assert new_context.order == context.order


def test_context_str(
    order_factory,
):
    order = order_factory()
    context = Context(order)
    context_str = str(context)
    assert f"Context: {order.get('id', None)} {order.get('type', None)}" == context_str
