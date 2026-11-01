from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

RU_MONTHS = {
    "января": 1,
    "январь": 1,
    "февраля": 2,
    "февраль": 2,
    "марта": 3,
    "март": 3,
    "апреля": 4,
    "апрель": 4,
    "мая": 5,
    "май": 5,
    "июня": 6,
    "июнь": 6,
    "июля": 7,
    "июль": 7,
    "августа": 8,
    "август": 8,
    "сентября": 9,
    "сентябрь": 9,
    "октября": 10,
    "октябрь": 10,
    "ноября": 11,
    "ноябрь": 11,
    "декабря": 12,
    "декабрь": 12,
}

_NUMERIC_DMY = re.compile(r"^(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?$")
_NUMERIC_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_TEXT_DMY = re.compile(r"^(\d{1,2})\s+([а-яё]+)(?:\s+(\d{4}))?$", re.IGNORECASE)


class ParseError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ParsedDate:
    day: int
    month: int
    year: int | None


def _normalize_year(raw: str | None) -> int | None:
    if raw is None:
        return None
    year = int(raw)
    if len(raw) == 2:
        year = 2000 + year if year <= 30 else 1900 + year
    return year


def _validate(day: int, month: int, year: int | None) -> None:
    if not 1 <= month <= 12:
        raise ParseError("bad_month")
    if not 1 <= day <= 31:
        raise ParseError("bad_day")
    check_year = year if year is not None else 2000
    try:
        date(check_year, month, day)
    except ValueError as exc:
        raise ParseError("bad_date") from exc


def parse_date(text: str) -> ParsedDate:
    """Accept DD.MM, DD.MM.YYYY, YYYY-MM-DD and '12 мая [1990]'."""
    value = " ".join(text.strip().lower().replace("ё", "е").split())
    if not value:
        raise ParseError("empty")

    iso = _NUMERIC_ISO.match(value)
    if iso:
        year, month, day = int(iso.group(1)), int(iso.group(2)), int(iso.group(3))
        _validate(day, month, year)
        return ParsedDate(day=day, month=month, year=year)

    numeric = _NUMERIC_DMY.match(value)
    if numeric:
        day, month = int(numeric.group(1)), int(numeric.group(2))
        year = _normalize_year(numeric.group(3))
        _validate(day, month, year)
        return ParsedDate(day=day, month=month, year=year)

    textual = _TEXT_DMY.match(value)
    if textual:
        day = int(textual.group(1))
        month = RU_MONTHS.get(textual.group(2))
        if month is None:
            raise ParseError("bad_month")
        year = _normalize_year(textual.group(3))
        _validate(day, month, year)
        return ParsedDate(day=day, month=month, year=year)

    raise ParseError("bad_format")


def validate_birth_date(parsed: ParsedDate, today: date | None = None) -> None:
    today = today or date.today()
    if parsed.year is None:
        return
    if parsed.year < 1900 or parsed.year > today.year:
        raise ParseError("bad_year")
    if date(parsed.year, parsed.month, parsed.day) > today:
        raise ParseError("future_date")


def validate_start_date(parsed: ParsedDate, today: date | None = None) -> None:
    today = today or date.today()
    if parsed.year is None:
        return
    if parsed.year < 1900 or parsed.year > today.year:
        raise ParseError("bad_year")
    if date(parsed.year, parsed.month, parsed.day) > today:
        raise ParseError("future_date")


def format_dmy(day: int, month: int, year: int | None = None) -> str:
    value = f"{day:02d}.{month:02d}"
    return f"{value}.{year}" if year else value
