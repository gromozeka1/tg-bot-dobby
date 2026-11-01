from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from dobby.db.models import Anniversary, Chat, Contact, User
from dobby.i18n import LOCALE_NAMES

T = Callable[..., str]


def main_menu(_: T) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("📅 Today")), KeyboardButton(text=_("👥 Contacts"))],
            [
                KeyboardButton(text=_("🎉 Anniversaries")),
                KeyboardButton(text=_("🔔 Subscriptions")),
            ],
            [KeyboardButton(text=_("⚙️ Settings")), KeyboardButton(text=_("➕ Add"))],
        ],
        resize_keyboard=True,
    )


def add_choice_kb(_: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=_("🎂 Contact"), callback_data="add:contact")
    builder.button(text=_("💍 Anniversary"), callback_data="add:anniversary")
    builder.button(text=_("⬅️ Back"), callback_data="menu:main")
    builder.adjust(2, 1)
    return builder.as_markup()


def menu_kb(_: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=_("🏠 Main menu"), callback_data="menu:main")
    return builder.as_markup()


def contact_list_kb(
    contacts: list[Contact], page: int, pages: int, _: T
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for contact in contacts:
        builder.button(
            text=f"{contact.full_name} · {contact.day:02d}.{contact.month:02d}",
            callback_data=f"c:view:{contact.id}",
        )
    builder.adjust(1)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=_("⬅️ Prev"), callback_data=f"c:page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="noop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(text=_("Next ➡️"), callback_data=f"c:page:{page + 1}"))
    if pages > 1:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text=_("➕ Add contact"), callback_data="add:contact"))
    builder.row(InlineKeyboardButton(text=_("🏠 Main menu"), callback_data="menu:main"))
    return builder.as_markup()


def contact_view_kb(contact: Contact, page: int, _: T) -> InlineKeyboardMarkup:
    muted = not (contact.notify_digest or contact.notify_group or contact.notify_direct)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=_("✏️ Name"), callback_data=f"c:editname:{contact.id}"),
        InlineKeyboardButton(text=_("📅 Date"), callback_data=f"c:editdate:{contact.id}"),
        InlineKeyboardButton(text=_("🆔 Telegram ID"), callback_data=f"c:edittg:{contact.id}"),
    )
    builder.row(
        InlineKeyboardButton(
            text=_("🔔 Unmute") if muted else _("🔕 Mute"),
            callback_data=f"c:mute:{contact.id}",
        ),
        InlineKeyboardButton(text=_("🗑 Delete"), callback_data=f"c:del:{contact.id}"),
    )
    builder.row(
        InlineKeyboardButton(text=_("⬅️ Back"), callback_data=f"c:page:{page}"),
        InlineKeyboardButton(text=_("🏠 Main menu"), callback_data="menu:main"),
    )
    return builder.as_markup()


def anniversary_list_kb(
    items: list[Anniversary], page: int, pages: int, _: T
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(
            text=f"{item.title} · {item.day:02d}.{item.month:02d}",
            callback_data=f"a:view:{item.id}",
        )
    builder.adjust(1)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=_("⬅️ Prev"), callback_data=f"a:page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="noop"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(text=_("Next ➡️"), callback_data=f"a:page:{page + 1}"))
    if pages > 1:
        builder.row(*nav)
    builder.row(
        InlineKeyboardButton(text=_("➕ Add anniversary"), callback_data="add:anniversary")
    )
    builder.row(InlineKeyboardButton(text=_("🏠 Main menu"), callback_data="menu:main"))
    return builder.as_markup()


def anniversary_view_kb(item: Anniversary, page: int, _: T) -> InlineKeyboardMarkup:
    muted = not (item.notify_digest or item.notify_group or item.notify_direct)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=_("✏️ Title"), callback_data=f"a:edittitle:{item.id}"),
        InlineKeyboardButton(text=_("📅 Date"), callback_data=f"a:editdate:{item.id}"),
    )
    builder.row(
        InlineKeyboardButton(
            text=_("🔔 Unmute") if muted else _("🔕 Mute"),
            callback_data=f"a:mute:{item.id}",
        ),
        InlineKeyboardButton(text=_("🗑 Delete"), callback_data=f"a:del:{item.id}"),
    )
    builder.row(
        InlineKeyboardButton(text=_("⬅️ Back"), callback_data=f"a:page:{page}"),
        InlineKeyboardButton(text=_("🏠 Main menu"), callback_data="menu:main"),
    )
    return builder.as_markup()


def confirm_kb(prefix: str, _: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=_("✅ Save"), callback_data=f"{prefix}:yes")
    builder.button(text=_("❌ Cancel"), callback_data=f"{prefix}:no")
    builder.adjust(2)
    return builder.as_markup()


def relation_kb(_: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=_("Family"), callback_data="rel:family")
    builder.button(text=_("Friend"), callback_data="rel:friend")
    builder.button(text=_("Colleague"), callback_data="rel:colleague")
    builder.button(text=_("Other"), callback_data="rel:other")
    builder.button(text=_("Skip"), callback_data="rel:skip")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def kind_kb(_: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=_("💍 Wedding"), callback_data="kind:wedding")
    builder.button(text=_("🕯 Memorial"), callback_data="kind:memorial")
    builder.button(text=_("🎉 Custom"), callback_data="kind:custom")
    builder.adjust(2, 1)
    return builder.as_markup()


def recurring_kb(_: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=_("🔁 Every year"), callback_data="rec:1")
    builder.button(text=_("1️⃣ Once"), callback_data="rec:0")
    builder.adjust(2)
    return builder.as_markup()


def target_kb(chats: list[Chat], _: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for chat in chats:
        builder.button(
            text=f"🎉 {chat.title or chat.tg_chat_id}", callback_data=f"tgt:{chat.id}"
        )
    builder.button(text=_("📩 Digest only"), callback_data="tgt:none")
    builder.adjust(1)
    return builder.as_markup()


def subscriptions_list_kb(
    items: list[Any], page: int, pages: int, filter_name: str, chat_count: int, _: T
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        icon = "🎂" if item.kind == "birthday" else "💍"
        flags = ""
        flags += "📩" if item.notify_digest else "·"
        flags += "🎉" if item.notify_group else "·"
        flags += "✉️" if item.notify_direct else "·"
        builder.button(
            text=f"{icon} {item.title} · {item.day:02d}.{item.month:02d}  {flags}",
            callback_data=f"sub:item:{item.kind}:{item.id}:{filter_name}:{page}",
        )
    builder.adjust(1)

    filters = [
        ("all", _("All")),
        ("birthdays", _("🎂 Birthdays")),
        ("anniversaries", _("💍 Anniversaries")),
        ("muted", _("🔕 Muted")),
    ]
    builder.row(
        *[
            InlineKeyboardButton(
                text=("· " if key == filter_name else "") + label,
                callback_data=f"sub:list:{key}:0",
            )
            for key, label in filters
        ]
    )

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text=_("⬅️ Prev"), callback_data=f"sub:list:{filter_name}:{page - 1}"
            )
        )
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="noop"))
    if page + 1 < pages:
        nav.append(
            InlineKeyboardButton(
                text=_("Next ➡️"), callback_data=f"sub:list:{filter_name}:{page + 1}"
            )
        )
    if pages > 1:
        builder.row(*nav)

    if chat_count == 0:
        builder.row(
            InlineKeyboardButton(
                text=_("ℹ️ Bind a group first"), callback_data="set:bindhint"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=_("🔕 Mute all birthdays"), callback_data="sub:bulk:birthday:1:all"
            ),
            InlineKeyboardButton(
                text=_("🔔 Unmute all"), callback_data="sub:bulk:all:0:all"
            ),
        )
    builder.row(InlineKeyboardButton(text=_("🏠 Main menu"), callback_data="menu:main"))
    return builder.as_markup()


def subscription_detail_kb(
    item: Any, filter_name: str, page: int, _: T
) -> InlineKeyboardMarkup:
    def mark(value: bool) -> str:
        return "✅" if value else "⬜"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"{mark(item.notify_digest)} 📩 {_('Digest')}",
            callback_data=f"sub:t:{item.kind}:{item.id}:digest:{filter_name}:{page}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{mark(item.notify_group)} 🎉 {_('Group')}",
            callback_data=f"sub:t:{item.kind}:{item.id}:group:{filter_name}:{page}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{mark(item.notify_direct)} ✉️ {_('Direct')}",
            callback_data=f"sub:t:{item.kind}:{item.id}:direct:{filter_name}:{page}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=_("⬅️ Back"), callback_data=f"sub:list:{filter_name}:{page}"
        ),
        InlineKeyboardButton(text=_("🏠 Main menu"), callback_data="menu:main"),
    )
    return builder.as_markup()


def settings_kb(user: User, chat_count: int, _: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=_("🕘 Digest time: {time}").format(time=user.digest_time),
            callback_data="set:time",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=_("🌍 Time zone: {zone}").format(zone=user.timezone),
            callback_data="set:tz",
        )
    )
    reminders = _("on") if user.reminders_enabled else _("off")
    builder.row(
        InlineKeyboardButton(
            text=_("⏰ Reminder: {state} ({days} d)").format(
                state=reminders, days=user.reminder_days_before
            ),
            callback_data="set:rem",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{'✅' if user.dm_enabled else '⬜'} 📩 {_('Digest')}",
            callback_data="set:dm",
        ),
        InlineKeyboardButton(
            text=f"{'✅' if user.group_enabled else '⬜'} 🎉 {_('Group')}",
            callback_data="set:group",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=_("🌐 Language: {lang}").format(
                lang=LOCALE_NAMES.get(user.locale, user.locale)
            ),
            callback_data="set:lang",
        )
    )
    if chat_count == 0:
        builder.row(
            InlineKeyboardButton(
                text=_("ℹ️ How to bind a group"), callback_data="set:bindhint"
            )
        )
    builder.row(InlineKeyboardButton(text=_("🏠 Main menu"), callback_data="menu:main"))
    return builder.as_markup()


def time_kb(current: str, _: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value in ("08:00", "09:00", "10:00", "12:00", "18:00"):
        label = f"· {value}" if value == current else value
        builder.button(text=label, callback_data=f"set:time:{value}")
    builder.button(text=_("✏️ Custom time"), callback_data="set:timecustom")
    builder.button(text=_("⬅️ Back"), callback_data="set:menu")
    builder.adjust(3, 2, 1, 1)
    return builder.as_markup()


def timezone_kb(current: str, _: T) -> InlineKeyboardMarkup:
    zones = [
        ("Europe/Minsk", _("Minsk (UTC+3)")),
        ("Europe/Moscow", _("Moscow (UTC+3)")),
        ("Europe/Warsaw", _("Warsaw")),
        ("Europe/Kyiv", _("Kyiv")),
        ("UTC", _("UTC")),
    ]
    builder = InlineKeyboardBuilder()
    for zone, label in zones:
        prefix = "· " if zone == current else ""
        builder.button(text=prefix + label, callback_data=f"set:tz:{zone}")
    builder.button(text=_("⬅️ Back"), callback_data="set:menu")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def reminder_kb(user: User, _: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"{'✅' if user.reminders_enabled else '⬜'} {_('Reminder enabled')}",
        callback_data="set:remtoggle",
    )
    for days in (1, 3, 7, 14):
        prefix = "· " if user.reminder_days_before == days else ""
        builder.button(text=f"{prefix}{days} {_('days')}", callback_data=f"set:remdays:{days}")
    builder.button(text=_("⬅️ Back"), callback_data="set:menu")
    builder.adjust(1, 4, 1)
    return builder.as_markup()


def language_kb(current: str, _: T) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, label in (("ru", "Русский"), ("en", "English")):
        prefix = "· " if current == code else ""
        builder.button(text=prefix + label, callback_data=f"set:lang:{code}")
    builder.button(text=_("⬅️ Back"), callback_data="set:menu")
    builder.adjust(2, 1)
    return builder.as_markup()
