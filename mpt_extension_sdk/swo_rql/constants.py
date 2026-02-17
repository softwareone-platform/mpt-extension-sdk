COMP = ("eq", "ne", "lt", "le", "gt", "ge")
SEARCH = ("like", "ilike")
LIST = ("in", "out")
NULL = "null"
EMPTY = "empty"
RQL_FUNCTIONS = ("null()",)

KEYWORDS = (*COMP, *SEARCH, *LIST, NULL, EMPTY)
