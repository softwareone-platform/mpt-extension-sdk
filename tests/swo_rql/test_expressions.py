from mpt_extension_sdk.swo_rql import R
from mpt_extension_sdk.swo_rql.query_builder import parse_kwargs


def test_in_and_namespaces(mock_product_ids_for_expression):
    q1 = R().n("agreement").n("product").n("id").in_(mock_product_ids_for_expression)
    q2 = R().agreement.product.id.in_(mock_product_ids_for_expression)
    assert str(q1) == str(q2)


def test_query_expression_get_querying_orders(mock_product_ids_for_expression):
    products_str = ",".join(mock_product_ids_for_expression)
    expected_rql_query = (
        f"and(in(agreement.product.id,({products_str})),eq(status,Querying))"
    )
    expected_url = (
        f"/commerce/orders?{expected_rql_query}&select=audit,parameters,lines,subscriptions,"
        f"subscriptions.lines,agreement,buyer&order=audit.created.at"
    )
    query = R().agreement.product.id.in_(mock_product_ids_for_expression) & R(
        status="Querying"
    )
    url = (
        f"/commerce/orders?{query}&select=audit,parameters,lines,subscriptions,"
        f"subscriptions.lines,agreement,buyer&order=audit.created.at"
    )
    assert expected_rql_query == str(query)
    assert expected_url == url


def test_in(mock_product_ids_for_expression):
    product_ids = ",".join(mock_product_ids_for_expression)
    q = R(product__id__in=mock_product_ids_for_expression)
    assert str(q) == f"in(product.id,({product_ids}))"


def test_repr(mock_product_ids_for_expression):
    product_ids = ",".join(mock_product_ids_for_expression)
    q = R(product__id__in=mock_product_ids_for_expression)
    assert repr(q) == f"<R(expr) in(product.id,({product_ids}))>"


def test_improper_op(mock_product_id_for_expression):
    products_expr = {"product__id__inn": mock_product_id_for_expression}
    q = parse_kwargs(products_expr)
    assert str(q) == f"['eq(product.id.inn,{mock_product_id_for_expression})']"


def test_parse_eq(mock_product_id_for_expression):
    products_expr = {"product__id__eq": mock_product_id_for_expression}
    q = parse_kwargs(products_expr)
    assert str(q) == f"['eq(product.id,{mock_product_id_for_expression})']"


def test_parse_like(mock_product_id_for_expression):
    products_expr = {"product__id__like": mock_product_id_for_expression}
    q = parse_kwargs(products_expr)
    assert str(q) == f"['like(product.id,{mock_product_id_for_expression})']"


def test_parse_null_op(mock_product_id_for_expression):
    products_expr = {"product__id__null": mock_product_id_for_expression}
    q = parse_kwargs(products_expr)
    assert str(q) == "['ne(product.id,null())']"
