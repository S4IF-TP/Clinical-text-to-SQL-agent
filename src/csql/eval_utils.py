"""Result-set comparison for execution accuracy."""

from collections import Counter
from datetime import date, datetime
from decimal import Decimal


def _norm_value(v):
    if v is None:
        return "∅"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int | float | Decimal):
        return f"{round(float(v), 2):.2f}"
    if isinstance(v, datetime | date):
        return v.isoformat()
    s = str(v).strip()
    try:  # numeric strings (e.g. observations.value) compare as numbers
        return f"{round(float(s), 2):.2f}"
    except ValueError:
        return s


def normalize(rows: list) -> Counter:
    """Multiset of rows; values rounded to 2dp, column order and row order ignored."""
    return Counter(tuple(sorted(_norm_value(v) for v in row)) for row in rows)


def results_match(pred_rows: list, gold_rows: list) -> bool:
    return normalize(pred_rows) == normalize(gold_rows)
