from typing import ClassVar

from rich.highlighter import ReprHighlighter as _ReprHighlighter
from rich.logging import RichHandler as _RichHandler


class ReprHighlighter(_ReprHighlighter):
    """Highlighter for MPT IDs."""
    accounts_prefixes = ("ACC", "BUY", "LCE", "MOD", "SEL", "USR", "AUSR", "UGR")
    catalog_prefixes = (
        "PRD",
        "ITM",
        "IGR",
        "PGR",
        "MED",
        "DOC",
        "TCS",
        "TPL",
        "WHO",
        "PRC",
        "LST",
        "AUT",
        "UNT",
    )
    commerce_prefixes = ("AGR", "ORD", "SUB", "REQ")
    aux_prefixes = ("FIL", "MSG")
    all_prefixes = (
        *accounts_prefixes,
        *catalog_prefixes,
        *commerce_prefixes,
        *aux_prefixes,
    )
    prefixes_pattern = "|".join(all_prefixes)
    pattern = rf"(?P<mpt_id>(?:{prefixes_pattern})(?:-\d{{4}})*)"
    highlights: ClassVar[list[str]] = [
        *_ReprHighlighter.highlights,
        pattern,
    ]


class RichHandler(_RichHandler):
    """Rich handler for logging with color support."""
    HIGHLIGHTER_CLASS = ReprHighlighter
