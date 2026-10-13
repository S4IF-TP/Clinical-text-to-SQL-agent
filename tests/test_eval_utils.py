from datetime import date
from decimal import Decimal

from csql.eval_utils import results_match


def test_row_and_column_order_ignored():
    assert results_match([(2, "b"), (1, "a")], [("a", 1), ("b", 2)])


def test_float_rounding():
    assert results_match([(Decimal("3.14159"),)], [(3.14,)])


def test_different_values_mismatch():
    assert not results_match([(1,)], [(2,)])


def test_duplicates_matter():
    assert not results_match([(1,), (1,)], [(1,)])


def test_dates_and_none():
    assert results_match([(date(2020, 1, 2), None)], [(None, date(2020, 1, 2))])


def test_numeric_string_equals_number():
    assert results_match([("120.0",)], [(120,)])
