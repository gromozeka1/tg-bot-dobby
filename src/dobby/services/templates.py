from __future__ import annotations

import random
from datetime import date
from html import escape

from babel.dates import format_date

from dobby.i18n import Translator, get_translator
from dobby.services.dates import Occurrence


def format_day(value: date, locale: str, *, with_year: bool = False) -> str:
    fmt = "d MMMM yyyy" if with_year else "d MMMM"
    try:
        return format_date(value, format=fmt, locale=locale)
    except Exception:  # pragma: no cover - unknown locale fallback
        return value.strftime("%d.%m.%Y" if with_year else "%d.%m")


def years_phrase(tr: Translator, years: int) -> str:
    return tr.ngettext("{n} year", "{n} years", years)


_ICONS = {"birthday": "🎂", "wedding": "💍", "memorial": "🕯"}


def _icon(event: Occurrence) -> str:
    if event.kind == "birthday":
        return _ICONS["birthday"]
    return _ICONS.get(event.subkind or "", "🎉")


def _line(tr: Translator, event: Occurrence) -> str:
    return _icon(event) + _bullet_line(tr, event).removeprefix("•")


def _bullet_line(tr: Translator, event: Occurrence) -> str:
    name = escape(event.title)
    if event.kind == "birthday":
        if event.years is not None:
            return tr.gettext("• <b>{name}</b> — birthday, turns {age}").format(
                name=name, age=event.years
            )
        return tr.gettext("• <b>{name}</b> — birthday").format(name=name)
    if event.years is not None:
        return tr.gettext("• <b>{title}</b> — {years}").format(
            title=name, years=years_phrase(tr, event.years)
        )
    return tr.gettext("• <b>{title}</b>").format(title=name)


def digest_text(locale: str, events: list[Occurrence]) -> str:
    tr = get_translator(locale)
    lines = [f"<b>{tr.gettext('Today')}</b>", ""]
    lines.extend(_line(tr, event) for event in events)
    closing = random.choice(
        [
            tr.gettext("Have a good day!"),
            tr.gettext("Make it a great day!"),
            tr.gettext("Don't forget to say hello!"),
            tr.gettext("Warm wishes to everyone!"),
            tr.gettext("Enjoy the celebrations!"),
            tr.gettext("Smiles and good mood today!"),
        ]
    )
    lines += ["", f"<i>{closing}</i>"]
    return "\n".join(lines)


def reminder_text(locale: str, events: list[Occurrence], days: int) -> str:
    tr = get_translator(locale)
    header = tr.ngettext("⏰ In {n} day", "⏰ In {n} days", days)
    lines = [f"<b>{header}</b>", ""]
    lines.extend(_line(tr, event) for event in events)
    return "\n".join(lines)


def group_text(locale: str, event: Occurrence) -> str:
    tr = get_translator(locale)
    name = escape(event.title)

    if event.kind == "birthday":
        if event.telegram_user_id:
            name = f'<a href="tg://user?id={event.telegram_user_id}">{name}</a>'
        text = tr.gettext("🎉 <b>Happy birthday, {name}!</b>").format(name=name)
        if event.years is not None:
            text += "\n" + tr.gettext("🎂 {age}").format(age=event.years)
        return text

    if event.years is None:
        if event.kind == "anniversary":
            return tr.gettext("🎉 <b>{title}</b>").format(title=name)
        return tr.gettext("🎉 <b>{title}</b>").format(title=name)

    years = years_phrase(tr, event.years)
    if event.subkind == "memorial":
        return tr.gettext("🕯 <b>In memory: {title}</b>\n{years}").format(
            title=name, years=years
        )
    if event.subkind == "wedding":
        return tr.gettext("💍 <b>{title}: {years}</b>").format(title=name, years=years)
    return tr.gettext("🎉 <b>{title}</b> — {years}").format(title=name, years=years)


def today_text(locale: str, events: list[Occurrence]) -> str:
    return digest_text(locale, events)


def upcoming_text(
    locale: str, days: list[tuple[date, list[Occurrence]]], window: int
) -> str:
    tr = get_translator(locale)
    lines = [f"📅 <b>{tr.gettext('Next {n} days').format(n=window)}</b>", ""]
    for day, events in days:
        lines.append(f"<b>{format_day(day, locale)}</b>")
        lines.extend(_line(tr, event) for event in events)
        lines.append("")
    return "\n".join(lines).strip()


def card_text(locale: str, event: Occurrence) -> str:
    return group_text(locale, event)
