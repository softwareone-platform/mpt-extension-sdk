import datetime as dt
from decimal import Decimal

import pytest

from mpt_extension_sdk.swo_rql.query_builder import RQLQuery, rql_encode


def test_create():
    result = RQLQuery()

    assert result.op == RQLQuery.EXPRESSION
    assert result.children == []
    assert result.negated is False


def test_create_with_field():
    rql_query = RQLQuery("field")

    rql_query.eq("value")  # act

    assert rql_query.op == RQLQuery.EXPRESSION
    assert str(rql_query) == "eq(field,'value')"


def test_create_single_kwarg():
    result = RQLQuery(id="ID")

    assert result.op == RQLQuery.EXPRESSION
    assert str(result) == "eq(id,'ID')"
    assert result.children == []
    assert result.negated is False


def test_create_multiple_kwargs():
    result = RQLQuery(id="ID", status__in=("a", "b"), ok=True)

    assert result.op == RQLQuery.AND
    assert str(result) == "and(eq(id,'ID'),in(status,(a,b)),eq(ok,'true'))"
    assert len(result.children) == 3
    assert result.children[0].op == RQLQuery.EXPRESSION
    assert result.children[0].children == []
    assert str(result.children[0]) == "eq(id,'ID')"
    assert result.children[1].op == RQLQuery.EXPRESSION
    assert result.children[1].children == []
    assert str(result.children[1]) == "in(status,(a,b))"
    assert result.children[2].op == RQLQuery.EXPRESSION
    assert result.children[2].children == []
    assert str(result.children[2]) == "eq(ok,'true')"


@pytest.mark.parametrize(
    ("op", "value", "expected_result"),
    [
        ("eq", "value", "'value'"),
        ("eq", "null()", "null()"),
        ("eq", "O'Reilly", "'O\\'Reilly'"),
        ("ne", True, "'true'"),
        ("lt", False, "'false'"),
        ("gt", 10, "'10'"),
        ("ge", 10.5, "'10.5'"),
        ("le", Decimal("32983.328238273"), "'32983.328238273'"),
        ("eq", dt.date(2024, 1, 2), "'2024-01-02'"),
        ("eq", dt.datetime(2024, 1, 2, 3, 4, 5, tzinfo=dt.UTC), "'2024-01-02T03:04:05+00:00'"),
    ],
)
def test_rql_encode_comparison_ops(op, value, expected_result):
    result = rql_encode(op, value)

    assert result == expected_result


@pytest.mark.parametrize(
    ("op", "value", "expected_result"),
    [
        ("like", "value*", "value*"),
        ("ilike", "Value", "Value"),
        ("like", True, "true"),
        ("ilike", 42, "42"),
        ("like", dt.date(2024, 1, 2), "2024-01-02"),
    ],
)
def test_rql_encode_non_comparison_ops(op, value, expected_result):
    result = rql_encode(op, value)

    assert result == expected_result


@pytest.mark.parametrize(
    ("op", "value", "expected_result"),
    [
        ("in", ("a", "b"), "a,b"),
        ("out", ["x", "y"], "x,y"),
        ("in", ("O'Reilly", "x"), "O\\'Reilly,x"),
        ("in", ("a,b", "c"), "a\\,b,c"),
    ],
)
def test_rql_encode_list_ops(op, value, expected_result):
    result = rql_encode(op, value)

    assert result == expected_result


@pytest.mark.parametrize(
    ("op", "value"),
    [
        ("eq", object()),
        ("in", "not-a-sequence"),
        ("in", ("ok", object())),
    ],
)
def test_rql_encode_invalid_value(op, value):
    with pytest.raises(TypeError):
        rql_encode(op, value)


@pytest.mark.parametrize(
    ("args", "expected_result"),
    [
        ({}, 0),
        ({"id": "ID"}, 1),
        ({"id": "ID", "status__in": ("a", "b")}, 2),
    ],
)
def test_len(args, expected_result):
    result = RQLQuery(**args)

    assert len(result) == expected_result


@pytest.mark.parametrize(
    ("args", "expected_result"),
    [
        ({}, False),
        ({"id": "ID"}, True),
        ({"id": "ID", "status__in": ("a", "b")}, True),
    ],
)
def test_bool(args, expected_result):
    result = bool(RQLQuery(**args))

    assert result is expected_result


def test_eq():
    result1 = RQLQuery()
    result2 = RQLQuery()

    result = result1 == result2

    assert result is True


def test_eq_with_one_param():
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(id="ID")

    result = result1 == result2

    assert result is True


def test_eq_with_one_param_invert():
    result1 = ~RQLQuery(id="ID")
    result2 = ~RQLQuery(id="ID")

    result = result1 == result2

    assert result is True


def test_eq_with_two_param_invert():
    result1 = RQLQuery(id="ID", status__in=("a", "b"))
    result2 = RQLQuery(id="ID", status__in=("a", "b"))

    result = result1 == result2

    assert result is True


def test_eq_not_equal():
    result1 = RQLQuery()
    result2 = RQLQuery(id="ID", status__in=("a", "b"))

    result = result1 == result2

    assert result is False


def test_or():
    result1 = RQLQuery()
    result2 = RQLQuery()

    result = result1 | result2

    assert result == result1
    assert result == result2


def test_or_with_same_param():
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(id="ID")

    result = result1 | result2

    assert result == result1
    assert result == result2


def test_or_with_different_param():
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(name="name")

    result = result1 | result2

    assert result != result1
    assert result != result2
    assert result.op == RQLQuery.OR
    assert result1 in result.children
    assert result2 in result.children


def test_and_or_with_param():
    result = RQLQuery(id="ID")

    assert result | RQLQuery() == result
    assert RQLQuery() | result == result


def test_or_merge():
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(name="name")
    result3 = RQLQuery(field="value")
    result4 = RQLQuery(field__in=("v1", "v2"))
    or1 = result1 | result2
    or2 = result3 | result4

    result = or1 | or2

    assert result.op == RQLQuery.OR
    assert len(result.children) == 4
    assert [result1, result2, result3, result4] == result.children


def test_or_merge_duplicate():
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(field="value")

    result = result1 | result2 | result2

    assert len(result) == 2
    assert result.op == RQLQuery.OR
    assert [result1, result2] == result.children


def test_and():
    result1 = RQLQuery()
    result2 = RQLQuery()

    result = result1 & result2

    assert result == result1
    assert result == result2


def test_and_with_same_param():
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(id="ID")

    result = result1 & result2

    assert result == result1
    assert result == result2


def test_and_with_different_param():
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(name="name")

    result = result1 & result2

    assert result != result1
    assert result != result2
    assert result.op == RQLQuery.AND
    assert result1 in result.children
    assert result2 in result.children


def test_and_not_equal():
    result = RQLQuery(id="ID")

    assert result & RQLQuery() == result
    assert RQLQuery() & result == result


def test_and_equal():
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(field="value")

    result = result1 & result2 & result2

    assert len(result) == 2
    assert result.op == RQLQuery.AND
    assert [result1, result2] == result.children


def test_and_or():  # noqa: AAA02
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(field="value")
    result3 = RQLQuery(other="value2")
    result4 = RQLQuery(inop__in=("a", "b"))

    result = result1 & result2 & (result3 | result4)

    assert result.op == RQLQuery.AND
    assert str(result) == "and(eq(id,'ID'),eq(field,'value'),or(eq(other,'value2'),in(inop,(a,b))))"

    result = result1 & result2 | result3

    assert str(result) == "or(and(eq(id,'ID'),eq(field,'value')),eq(other,'value2'))"

    result = result1 & (result2 | result3)

    assert str(result) == "and(eq(id,'ID'),or(eq(field,'value'),eq(other,'value2')))"

    result = (result1 & result2) | (result3 & result4)

    assert (
        str(result)
        == "or(and(eq(id,'ID'),eq(field,'value')),and(eq(other,'value2'),in(inop,(a,b))))"
    )

    result = (result1 & result2) | ~result3

    assert str(result) == "or(and(eq(id,'ID'),eq(field,'value')),not(eq(other,'value2')))"


def test_and_merge():
    result1 = RQLQuery(id="ID")
    result2 = RQLQuery(name="name")
    result3 = RQLQuery(field="value")
    result4 = RQLQuery(field__in=("v1", "v2"))
    and1 = result1 & result2
    and2 = result3 & result4

    result = and1 & and2

    assert result.op == RQLQuery.AND
    assert len(result.children) == 4
    assert [result1, result2, result3, result4] == result.children


@pytest.mark.parametrize("op", ["eq", "ne", "gt", "ge", "le", "lt"])
def test_dotted_path_comp(op):
    rql_query = RQLQuery
    assert str(getattr(rql_query().asset.id, op)("value")) == f"{op}(asset.id,'value')"
    assert str(getattr(rql_query().asset.id, op)(True)) == f"{op}(asset.id,'true')"  # noqa: FBT003
    assert str(getattr(rql_query().asset.id, op)(False)) == f"{op}(asset.id,'false')"  # noqa: FBT003
    assert str(getattr(rql_query().asset.id, op)(10)) == f"{op}(asset.id,'10')"
    assert str(getattr(rql_query().asset.id, op)(10.678937)) == f"{op}(asset.id,'10.678937')"
    # BL
    decimal = Decimal("32983.328238273")
    assert str(getattr(rql_query().asset.id, op)(decimal)) == f"{op}(asset.id,'{decimal!s}')"
    # BL
    now = dt.datetime.now(tz=dt.UTC).date()
    assert str(getattr(rql_query().asset.id, op)(now)) == f"{op}(asset.id,'{now.isoformat()}')"
    # BL
    now = dt.datetime.now(tz=dt.UTC)
    assert str(getattr(rql_query().asset.id, op)(now)) == f"{op}(asset.id,'{now.isoformat()}')"

    # BL
    class Test:
        pass

    # BL
    test = Test()

    with pytest.raises(TypeError):
        getattr(rql_query().asset.id, op)(test)


@pytest.mark.parametrize("op", ["like", "ilike"])
def test_dotted_path_search(op):
    rql_query = RQLQuery  # act

    assert str(getattr(rql_query().asset.id, op)("value")) == f"{op}(asset.id,value)"
    assert str(getattr(rql_query().asset.id, op)("*value")) == f"{op}(asset.id,*value)"
    assert str(getattr(rql_query().asset.id, op)("value*")) == f"{op}(asset.id,value*)"
    assert str(getattr(rql_query().asset.id, op)("*value*")) == f"{op}(asset.id,*value*)"


@pytest.mark.parametrize(
    ("method", "op"),
    [
        ("in_", "in"),
        ("oneof", "in"),
        ("out", "out"),
    ],
)
def test_dotted_path_list(method, op):
    rql_query = RQLQuery
    rexpr = getattr(rql_query().asset.id, method)(("first", "second"))
    # BL
    assert str(rexpr) == f"{op}(asset.id,(first,second))"
    # BL
    rexpr = getattr(rql_query().asset.id, method)(["first", "second"])
    assert str(rexpr) == f"{op}(asset.id,(first,second))"

    with pytest.raises(TypeError):
        getattr(rql_query().asset.id, method)("Test")


@pytest.mark.parametrize(
    ("expr", "value", "expected_op"),
    [
        ("null", True, "eq"),
        ("null", False, "ne"),
        ("empty", True, "eq"),
        ("empty", False, "ne"),
    ],
)
def test_dotted_path_bool(expr, value, expected_op):
    rql_query = RQLQuery

    result = str(getattr(rql_query().asset.id, expr)(value))

    assert result == f"{expected_op}(asset.id,{expr}())"


def test_dotted_path_already_evaluated():
    result = RQLQuery().first.second.eq("value")

    with pytest.raises(AttributeError):
        _ = result.third


def test_str():  # noqa: AAA01
    result1 = str(RQLQuery(id="ID"))
    result2 = str(~RQLQuery(id="ID"))
    result3 = str(~RQLQuery(id="ID", field="value"))

    assert result1 == "eq(id,'ID')"
    assert result2 == "not(eq(id,'ID'))"
    assert result3 == "not(and(eq(id,'ID'),eq(field,'value')))"
    assert not str(RQLQuery())


def test_hash():
    rql_query = RQLQuery(id="ID", field="value")
    new_set = set()
    new_set.add(rql_query)
    new_set.add(rql_query)

    result = len(new_set)

    assert result == 1


def test_empty():
    result = RQLQuery("value").empty()

    assert result == RQLQuery("value").empty(value=True)
    assert str(RQLQuery("value").empty()) == "eq(value,empty())"
    assert str(RQLQuery("value").not_empty()) == "ne(value,empty())"
    assert RQLQuery("value").empty(value=False) == RQLQuery("value").not_empty()
