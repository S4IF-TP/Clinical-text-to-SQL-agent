import pytest

from csql.llm import _retry_after_seconds


def test_minutes_and_seconds():
    msg = "Rate limit reached ... on tokens per day (TPD): Limit 200000. Please try again in 3m6.624s."
    assert _retry_after_seconds(msg) == pytest.approx(186.624)


def test_seconds_only():
    assert _retry_after_seconds("Please try again in 7.5s.") == pytest.approx(7.5)


def test_request_too_large_is_not_waited():
    assert _retry_after_seconds("Request too large for model ... Please try again in 1s") is None


def test_unrelated_message():
    assert _retry_after_seconds("Invalid API key") is None
