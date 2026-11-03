"""Calibrated argument matching for deterministic benchmark tools."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

_RELATIVE_DATE_OFFSETS = {
    "today": 0,
    "tonight": 0,
    "this morning": 0,
    "this afternoon": 0,
    "this evening": 0,
    "tomorrow": 1,
}


def _equivalent_value(actual: Any, expected: Any, reference_date: date) -> bool:
    if actual == expected:
        return True
    if isinstance(actual, str) and isinstance(expected, str):
        offset = _RELATIVE_DATE_OFFSETS.get(expected.casefold())
        if offset is not None:
            return actual == (reference_date + timedelta(days=offset)).isoformat()
    return False


def arguments_match(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    reference_date: date | None = None,
) -> bool:
    """Match exact arguments while accepting calibrated relative-date normalization."""
    if actual.keys() != expected.keys():
        return False
    today = reference_date or date.today()
    return all(_equivalent_value(actual[key], expected[key], today) for key in expected)


def normalized_argument_variant(
    expected: Mapping[str, Any], *, reference_date: date | None = None
) -> dict[str, Any]:
    """Return the ISO-date form an agent may reasonably derive from relative dates."""
    today = reference_date or date.today()
    normalized = dict(expected)
    for key, value in expected.items():
        if isinstance(value, str):
            offset = _RELATIVE_DATE_OFFSETS.get(value.casefold())
            if offset is not None:
                normalized[key] = (today + timedelta(days=offset)).isoformat()
    return normalized
