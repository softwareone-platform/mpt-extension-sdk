from mpt_extension_sdk.swo_rql import constants


def parse_kwargs(query_dict):
    query = []
    for lookup, value in query_dict.items():
        tokens = lookup.split("__")
        if len(tokens) == 1:
            #  field=value
            field = tokens[0]
            value = rql_encode("eq", value)
            query.append(f"eq({field},{value})")
            continue
        op = tokens[-1]
        if op not in constants.KEYWORDS:
            # field__nested=value
            field = ".".join(tokens)
            value = rql_encode("eq", value)
            query.append(f"eq({field},{value})")
            continue
        field = ".".join(tokens[:-1])
        if op in constants.COMP or op in constants.SEARCH:
            value = rql_encode(op, value)
            query.append(f"{op}({field},{value})")
            continue
        if op in constants.LIST:
            value = rql_encode(op, value)
            query.append(f"{op}({field},({value}))")
            continue

        cmpop = "eq" if value is True else "ne"
        expr = "null()" if op == constants.NULL else "empty()"
        query.append(f"{cmpop}({field},{expr})")

    return query


def rql_encode(op, value):
    from datetime import date, datetime
    from decimal import Decimal

    if op not in constants.LIST:
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int | float | Decimal):
            return str(value)
        if isinstance(value, date | datetime):
            return value.isoformat()
    if op in constants.LIST and isinstance(value, list | tuple):
        return ",".join(value)
    raise TypeError(f"the `{op}` operator doesn't support the {type(value)} type.")


class RQLQuery:
    """
    Helper class to construct complex RQL queries.

    Usage:

    ```py3
        rql = R(field='value', field2__in=('v1', 'v2'), field3__empty=True)
    ```
    !!! note
        All the lookups expressed as keyword arguments are combined together with a logical `and`.


    Using the ``n`` method:

    ```py3
        rql = (
            R().n('field').eq('value')
            & R().n('field2').anyof(('v1', 'v2'))
            & R().n('field3').empty(True)
        )
    ```

    The previous query can be expressed in a more concise form like:

    ```py3
    rql = R().field.eq('value') & R().field2.anyof(('v1', 'v2')) & r.field3.empty(True)
    ```

    ```py3
    rql = R("field").eq("value")
    ```

    The R object support the bitwise operators `&`, `|` and `~`.

    Nested fields can be expressed using dot notation:

    ```py3
    rql = R().n('nested.field').eq('value')
    ```

    or

    ```py3
    rql = R().nested.field.eq('value')
    ```
    """

    AND = "and"
    OR = "or"
    EXPRESSION = "expr"

    def __init__(
        self,
        _field=None,
        *,
        _op=EXPRESSION,
        _children=None,
        _negated=False,
        _expr=None,
        **kwargs,
    ):
        self.op = _op
        self.children = _children or []
        self.negated = _negated
        self.expr = _expr
        self._path = []
        self._field = None
        if _field:
            self.n(_field)
        if len(kwargs) == 1:
            self.op = self.EXPRESSION
            self.expr = parse_kwargs(kwargs)[0]
        if len(kwargs) > 1:
            self.op = self.AND
            for token in parse_kwargs(kwargs):
                self.children.append(RQLQuery(_expr=token))

    def __len__(self):
        if self.op == self.EXPRESSION:
            if self.expr:
                return 1
            return 0
        return len(self.children)

    def __bool__(self):
        return bool(self.children) or bool(self.expr)

    def __eq__(self, other):
        return (
            self.op == other.op
            and self.children == other.children
            and self.negated == other.negated
            and self.expr == other.expr
        )

    def __hash__(self):
        return hash(
            (
                self.op,
                self.expr,
                self.negated,
                *(hash(value) for value in self.children),
            ),
        )

    def __repr__(self):
        if self.op == self.EXPRESSION:
            return f"<R({self.op}) {self.expr}>"
        return f"<R({self.op})>"

    def __and__(self, other):
        return self._join(other, self.AND)

    def __or__(self, other):
        return self._join(other, self.OR)

    def __invert__(self):
        query = RQLQuery(_op=self.AND, _expr=self.expr, _negated=True)
        query._append(self)
        return query

    def __getattr__(self, name):
        return self.n(name)

    def __str__(self):
        return self._to_string(self)

    def n(self, name):
        """
        Set the current field for this `R` object.

        Args:
            name (str): Name of the field.
        """
        if self._field:
            raise AttributeError("Already evaluated")

        self._path.extend(name.split("."))
        return self

    def ne(self, value):
        """
        Apply the `ne` operator to the field this `R` object refers to.

        Args:
            value (str): The value to which compare the field.
        """
        return self._bin("ne", value)

    def eq(self, value):
        """
        Apply the `eq` operator to the field this `R` object refers to.

        Args:
            value (str): The value to which compare the field.
        """
        return self._bin("eq", value)

    def lt(self, value):
        """
        Apply the `lt` operator to the field this `R` object refers to.

        Args:
            value (str): The value to which compare the field.
        """
        return self._bin("lt", value)

    def le(self, value):
        """
        Apply the `le` operator to the field this `R` object refers to.

        Args:
            value (str): The value to which compare the field.
        """
        return self._bin("le", value)

    def gt(self, value):
        """
        Apply the `gt` operator to the field this `R` object refers to.

        Args:
            value (str): The value to which compare the field.
        """
        return self._bin("gt", value)

    def ge(self, value):
        """
        Apply the `ge` operator to the field this `R` object refers to.

        Args:
            value (str): The value to which compare the field.
        """
        return self._bin("ge", value)

    def out(self, value: list[str]):
        """
        Apply the `out` operator to the field this `R` object refers to.

        Args:
            value (list[str]): The list of values to which compare the field.
        """
        return self._list("out", value)

    def in_(self, value):
        return self._list("in", value)

    def oneof(self, value: list[str]):
        """
        Apply the `in` operator to the field this `R` object refers to.

        Args:
            value (list[str]): The list of values to which compare the field.
        """
        return self._list("in", value)

    def null(self, value: list[str]):
        """
        Apply the `null` operator to the field this `R` object refers to.

        Args:
            value (list[str]): The value to which compare the field.
        """
        return self._bool("null", value)

    def empty(self, value: bool = True):
        """
        Apply the `empty` operator to the field this `R` object refers to.

        Usage: `R().field.empty()

        For not empty: `R().field.empty(False)` or `R().field.not_empty()`
        """
        return self._bool("empty", value)

    def not_empty(self):
        """
        Apply the `not_empty` operator to the field this `R` object refers to.
        """
        query = self._bool("empty", False)
        return query

    def like(self, value: list[str]):
        """
        Apply the `like` operator to the field this `R` object refers to.

        Args:
            value (list[str]): The value to which compare the field.
        """
        return self._bin("like", value)

    def ilike(self, value: list[str]):
        """
        Apply the `ilike` operator to the field this `R` object refers to.

        Args:
            value (list[str]): The value to which compare the field.
        """
        return self._bin("ilike", value)

    def _bin(self, op, value):
        self._field = ".".join(self._path)
        value = rql_encode(op, value)
        self.expr = f"{op}({self._field},{value})"
        return self

    def _list(self, op, value):
        self._field = ".".join(self._path)
        value = rql_encode(op, value)
        self.expr = f"{op}({self._field},({value}))"
        return self

    def _bool(self, expr, value):
        self._field = ".".join(self._path)
        if bool(value) is False:
            self.expr = f"ne({self._field},{expr}())"
            return self
        self.expr = f"eq({self._field},{expr}())"
        return self

    def _to_string(self, query):
        tokens = []
        if query.expr:
            if query.negated:
                return f"not({query.expr})"
            return query.expr
        for c in query.children:
            if c.expr:
                if c.negated:
                    tokens.append(f"not({c.expr})")
                else:
                    tokens.append(c.expr)
                continue
            tokens.append(self._to_string(c))

        if not tokens:
            return ""

        if query.negated:
            return f'not({query.op}({",".join(tokens)}))'
        return f'{query.op}({",".join(tokens)})'

    def _copy(self, other):
        return RQLQuery(
            _op=other.op,
            _children=other.children[:],
            _expr=other.expr,
        )

    def _join(self, other, op):
        if self == other:
            return self._copy(self)
        if not other:
            return self._copy(self)
        if not self:
            return self._copy(other)

        query = RQLQuery(_op=op)
        query._append(self)
        query._append(other)
        return query

    def _append(self, other):
        if other in self.children:
            return other

        if (
            other.op == self.op or (len(other) == 1 and other.op != self.EXPRESSION)
        ) and not other.negated:
            self.children.extend(other.children)
            return self

        self.children.append(other)
        return self


R = RQLQuery
