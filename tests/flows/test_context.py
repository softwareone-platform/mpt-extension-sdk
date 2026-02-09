from mpt_extension_sdk.flows.context import (
    ORDER_TYPE_CHANGE,
    ORDER_TYPE_PURCHASE,
    ORDER_TYPE_TERMINATION,
    Context,
)


def test_context_get_order_id(order):
    context = Context(order)

    result = context.order_id

    assert result == order["id"]


def test_context_get_order_type(order):
    context = Context(order)

    result = context.order_type

    assert result == order["type"]


def test_context_get_product_id(order):
    context = Context(order)

    result = context.product_id

    assert result == order.get("product", {}).get("id", None)


def test_context_is_purchase_order(order_factory):
    order = order_factory(order_type=ORDER_TYPE_PURCHASE)
    context = Context(order)

    result = context.is_purchase_order()

    assert result


def test_context_is_change_order(order_factory):
    order = order_factory(order_type=ORDER_TYPE_CHANGE)
    context = Context(order)

    result = context.is_change_order()

    assert result


def test_context_is_termination_order(order_factory):
    order = order_factory(order_type=ORDER_TYPE_TERMINATION)
    context = Context(order)

    result = context.is_termination_order()

    assert result


def test_from_context(order):
    context = Context(order)

    result = Context.from_context(context)

    assert result.order == context.order


def test_context_str(order):
    context = Context(order)

    result = str(context)

    assert result == f"Context: {order.get('id', None)} {order.get('type', None)}"
