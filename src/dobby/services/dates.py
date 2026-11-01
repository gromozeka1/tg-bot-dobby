from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

FEB29_FALLBACK_DAY = 28


def is_leap(year: int) -> bool:
    return calendar.isleap(year)


def effective_day(year: int, month: int, day: int) -> int:
    """Feb 29 falls back to Feb 28 in non-leap years."""
    if month == 2 and day == 29 and not is_leap(year):
        return FEB29_FALLBACK_DAY
    return day


def occurrence_in_year(year: int, month: int, day: int) -> date:
    return date(year, month, effective_day(year, month, day))


def is_event_on(day: int, month: int, on_date: date) -> bool:
    return on_date.month == month and on_date.day == effective_day(
        on_date.year, month, day
    )


def next_occurrence(day: int, month: int, after: date, recurring: bool = True) -> date:
    this_year = occurrence_in_year(after.year, month, day)
    if this_year >= after:
        return this_year
    if not recurring:
        return this_year
    return occurrence_in_year(after.year + 1, month, day)


def days_until(day: int, month: int, after: date) -> int:
    return (next_occurrence(day, month, after) - after).days


def age_on(birth_year: int | None, occurrence: date) -> int | None:
    if birth_year is None:
        return None
    age = occurrence.year - birth_year
    return age if age > 0 else None


def years_since(start_year: int | None, occurrence: date) -> int | None:
    if start_year is None:
        return None
    years = occurrence.year - start_year
    return years if years > 0 else None


def now_in(tz_name: str, *, now: datetime | None = None) -> datetime:
    tz = ZoneInfo(tz_name)
    if now is None:
        return datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("UTC"))
    return now.astimezone(tz)


def parse_hhmm(value: str) -> time:
    hours, minutes = value.strip().split(":")
    return time(int(hours), int(minutes))


@dataclass(frozen=True, slots=True)
class Occurrence:
    """One birthday or anniversary happening on a concrete date."""

    kind: str  # "birthday" | "anniversary"
    id: int
    title: str
    date: date
    years: int | None
    notify_digest: bool
    notify_group: bool
    notify_direct: bool
    target_chat_id: int | None
    telegram_username: str | None = None
    telegram_user_id: int | None = None
    subkind: str | None = None  # wedding | memorial | custom for anniversaries
