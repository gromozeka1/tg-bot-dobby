from __future__ import annotations

from datetime import date

import pytest

from dobby.services.dates import (
    age_on,
    is_event_on,
    next_occurrence,
    occurrence_in_year,
    years_since,
)


def test_feb29_falls_back_to_28_in_non_leap_year() -> None:
    assert occurrence_in_year(2026, 2, 29) == date(2026, 2, 28)
    assert occurrence_in_year(2028, 2, 29) == date(2028, 2, 29)


def test_is_event_on_handles_feb29() -> None:
    assert is_event_on(29, 2, date(2026, 2, 28))
    assert not is_event_on(29, 2, date(2026, 2, 27))
    assert is_event_on(29, 2, date(2028, 2, 29))
    assert not is_event_on(29, 2, date(2028, 2, 28))


def test_next_occurrence_rolls_to_next_year() -> None:
    assert next_occurrence(5, 3, date(2026, 3, 6)) == date(2027, 3, 5)
    assert next_occurrence(5, 3, date(2026, 3, 5)) == date(2026, 3, 5)


def test_next_occurrence_non_recurring_returns_this_year() -> None:
    assert next_occurrence(5, 3, date(2026, 3, 6), recurring=False) == date(2026, 3, 5)


def test_age_and_years() -> None:
    assert age_on(1990, date(2026, 5, 15)) == 36
    assert age_on(None, date(2026, 5, 15)) is None
    assert age_on(2026, date(2026, 5, 15)) is None
    assert years_since(2010, date(2026, 5, 15)) == 16
    assert years_since(None, date(2026, 5, 15)) is None


def test_invalid_month_raises() -> None:
    with pytest.raises(ValueError):
        occurrence_in_year(2026, 13, 1)
