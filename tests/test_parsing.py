from __future__ import annotations

from datetime import date

import pytest

from dobby.utils.parsing import (
    ParseError,
    parse_date,
    validate_birth_date,
    validate_start_date,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12.05", (12, 5, None)),
        ("1.2.1990", (1, 2, 1990)),
        ("12.05.1990", (12, 5, 1990)),
        ("1990-05-12", (12, 5, 1990)),
        ("12 мая 1990", (12, 5, 1990)),
        ("12 мая", (12, 5, None)),
        ("12 МАЯ", (12, 5, None)),
    ],
)
def test_parse_date(value: str, expected: tuple[int, int, int | None]) -> None:
    parsed = parse_date(value)
    assert (parsed.day, parsed.month, parsed.year) == expected


@pytest.mark.parametrize("value", ["", "32.01", "12.13", "hello", "31.02.1990"])
def test_parse_date_rejects_invalid(value: str) -> None:
    with pytest.raises(ParseError):
        parse_date(value)


def test_validate_birth_date() -> None:
    validate_birth_date(parse_date("29.02.2000"), today=date(2026, 11, 1))
    with pytest.raises(ParseError):
        validate_birth_date(parse_date("01.01.2030"), today=date(2026, 11, 1))
    with pytest.raises(ParseError):
        validate_birth_date(parse_date("01.01.1800"), today=date(2026, 11, 1))


def test_validate_start_date() -> None:
    validate_start_date(parse_date("12.05.2015"), today=date(2026, 11, 1))
    with pytest.raises(ParseError):
        validate_start_date(parse_date("12.05.2030"), today=date(2026, 11, 1))
