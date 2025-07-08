COMP = ("eq", "ne", "lt", "le", "gt", "ge")
SEARCH = ("like", "ilike")
LIST = ("in", "out")
NULL = "null"
EMPTY = "empty"

KEYWORDS = (*COMP, *SEARCH, *LIST, NULL, EMPTY)
