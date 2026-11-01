"""Generate the Russian gettext catalog from the English msgids.

Run after changing UI strings:
    .venv\\Scripts\\python.exe scripts\\build_ru_po.py
"""

from __future__ import annotations

from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parents[1]
POT = ROOT / "src" / "dobby" / "locales" / "dobby.pot"
PO = ROOT / "src" / "dobby" / "locales" / "ru" / "LC_MESSAGES" / "dobby.po"

RU = {
    "⚠️ Bot error: {error}": "⚠️ Ошибка бота: {error}",
    "📅 Today": "📅 Сегодня",
    "👥 Contacts": "👥 Контакты",
    "🎉 Anniversaries": "🎉 Годовщины",
    "🔔 Subscriptions": "🔔 Подписки",
    "⚙️ Settings": "⚙️ Настройки",
    "➕ Add": "➕ Добавить",
    "🎂 Contact": "🎂 Контакт",
    "💍 Anniversary": "💍 Годовщина",
    "⬅️ Back": "⬅️ Назад",
    "🏠 Main menu": "🏠 Главное меню",
    "⬅️ Prev": "⬅️ Назад",
    "Next ➡️": "Вперёд ➡️",
    "➕ Add contact": "➕ Добавить контакт",
    "✏️ Name": "✏️ Имя",
    "📅 Date": "📅 Дата",
    "🔔 Unmute": "🔔 Включить",
    "🔕 Mute": "🔕 Отключить",
    "🗑 Delete": "🗑 Удалить",
    "➕ Add anniversary": "➕ Добавить годовщину",
    "✏️ Title": "✏️ Название",
    "✅ Save": "✅ Сохранить",
    "❌ Cancel": "❌ Отмена",
    "Family": "Семья",
    "Friend": "Друг",
    "Colleague": "Коллега",
    "Other": "Другое",
    "Skip": "Пропустить",
    "💍 Wedding": "💍 Свадьба",
    "🕯 Memorial": "🕯 Память",
    "🎉 Custom": "🎉 Другое",
    "🔁 Every year": "🔁 Каждый год",
    "1️⃣ Once": "1️⃣ Один раз",
    "📩 Digest only": "📩 Только дайджест",
    "All": "Все",
    "🎂 Birthdays": "🎂 Дни рождения",
    "💍 Anniversaries": "💍 Годовщины",
    "🔕 Muted": "🔕 Отключённые",
    "ℹ️ Bind a group first": "ℹ️ Сначала привяжите группу",
    "🔕 Mute all birthdays": "🔕 Отключить все ДР",
    "🔔 Unmute all": "🔔 Включить всё",
    "Digest": "Дайджест",
    "Group": "Группа",
    "Direct": "Лично",
    "🕘 Digest time: {time}": "🕘 Время дайджеста: {time}",
    "🌍 Time zone: {zone}": "🌍 Часовой пояс: {zone}",
    "on": "вкл",
    "off": "выкл",
    "⏰ Reminder: {state} ({days} d)": "⏰ Напоминание: {state} (за {days} дн.)",
    "🌐 Language: {lang}": "🌐 Язык: {lang}",
    "ℹ️ How to bind a group": "ℹ️ Как привязать группу",
    "✏️ Custom time": "✏️ Своё время",
    "Minsk (UTC+3)": "Минск (UTC+3)",
    "Moscow (UTC+3)": "Москва (UTC+3)",
    "Warsaw": "Варшава",
    "Kyiv": "Киев",
    "UTC": "UTC",
    "Reminder enabled": "Напоминание включено",
    "days": "дн.",
    "🎗 {kind}": "🎗 {kind}",
    "📩 Digest: {state}": "📩 Дайджест: {state}",
    "🎉 Group: {state}": "🎉 Группа: {state}",
    "✉️ Direct: {state}": "✉️ Лично: {state}",
    "🎉 Anniversaries ({total})": "🎉 Годовщины ({total})",
    "No anniversaries yet. Add the first one with /addanniversary.": (
        "Годовщин пока нет. Добавьте первую: /addanniversary."
    ),
    "What is the occasion? For example: Wedding, Mom's memorial, First date.": (
        "Какой повод? Например: Свадьба, Годовщина памяти мамы, Первое свидание."
    ),
    "Please send a title up to 255 characters.": ("Пришлите название не длиннее 255 символов."),
    "Date? For example 12.05 or 12.05.2015.": "Дата? Например 12.05 или 12.05.2015.",
    "Invalid date. Try 12.05 or 12.05.2015.": ("Неверная дата. Попробуйте 12.05 или 12.05.2015."),
    "What kind of date is this?": "Что это за дата?",
    "Start year? Send «-» if you don't know.": ("Год начала? Пришлите «-», если не знаете."),
    "Repeat every year?": "Повторять каждый год?",
    "Invalid year. Send a year like 2015 or «-».": (
        "Неверный год. Пришлите год, например 2015, или «-»."
    ),
    "Where should I congratulate?": "Где поздравлять?",
    "This group is no longer available.": "Эта группа больше недоступна.",
    "Digest only": "Только дайджест",
    "Check the data:": "Проверьте данные:",
    "Title: {title}": "Название: {title}",
    "Date: {date}": "Дата: {date}",
    "Kind: {kind}": "Тип: {kind}",
    "Repeat: {value}": "Повтор: {value}",
    "every year": "каждый год",
    "once": "один раз",
    "Group: {chat}": "Группа: {chat}",
    "Cancelled. Nothing was saved.": "Отменено. Ничего не сохранено.",
    "Saved.": "Сохранено.",
    "✅ Saved.": "✅ Сохранено.",
    "New anniversary": "Новая годовщина",
    "Delete {name}?": "Удалить «{name}»?",
    "🗑 Deleted.": "🗑 Удалено.",
    "Send a new title.": "Пришлите новое название.",
    "Anniversary not found.": "Годовщина не найдена.",
    "Send a new date: 12.05 or 12.05.2015.": ("Пришлите новую дату: 12.05 или 12.05.2015."),
    "Cancelled.": "Отменено.",
    "🗑 Delete my data": "🗑 Удалить мои данные",
    "This permanently deletes your account and all saved data. Continue?": (
        "Это навсегда удалит ваш аккаунт и все сохранённые данные. Продолжить?"
    ),
    "Deleted.": "Удалено.",
    "Your account and saved data were deleted.": "Ваш аккаунт и сохранённые данные удалены.",
    "I can remember birthdays and anniversaries and congratulate people.\n\n"
    "/today — what is today\n"
    "/upcoming — the next 14 days\n"
    "/contacts — contact list\n"
    "/addcontact — add a contact\n"
    "/anniversaries — anniversary list\n"
    "/addanniversary — add an anniversary\n"
    "/subscriptions — what goes into the digest and the group\n"
    "/settings — time, reminders, language\n"
    "/bindgroup — bind this group (send it in the group)\n"
    "/cancel — cancel the current step": (
        "Я помню дни рождения и годовщины и поздравляю людей.\n\n"
        "/today — что сегодня\n"
        "/upcoming — ближайшие 14 дней\n"
        "/contacts — список контактов\n"
        "/addcontact — добавить контакт\n"
        "/anniversaries — список годовщин\n"
        "/addanniversary — добавить годовщину\n"
        "/subscriptions — что попадает в дайджест и группу\n"
        "/settings — время, напоминания, язык\n"
        "/bindgroup — привязать группу (отправьте в группе)\n"
        "/cancel — отменить текущий шаг"
    ),
    "Choose an action:": "Выберите действие:",
    "Nothing to do here.": "Здесь ничего нет.",
    "Add me to the group, make me an administrator (or allow messages), "
    "then send /bindgroup in that group.": (
        "Добавьте меня в группу, сделайте администратором "
        "(или разрешите сообщения), затем отправьте /bindgroup в этой группе."
    ),
    "👥 {relation}": "👥 {relation}",
    "👥 Contacts ({total})": "👥 Контакты ({total})",
    "No contacts yet. Add the first one with /addcontact.": (
        "Контактов пока нет. Добавьте первый: /addcontact."
    ),
    "What is the name? Send /cancel to abort.": ("Как зовут? Отправьте /cancel для отмены."),
    "Please send a name up to 255 characters.": ("Пришлите имя не длиннее 255 символов."),
    "Date of birth? For example 12.05 or 12.05.1990. Send /cancel to abort.": (
        "Дата рождения? Например 12.05 или 12.05.1990. Отправьте /cancel для отмены."
    ),
    "Relation?": "Кем приходится?",
    "Invalid date. Try 12.05 or 12.05.1990.": ("Неверная дата. Попробуйте 12.05 или 12.05.1990."),
    "Birth year? Send «-» if you don't know.": ("Год рождения? Пришлите «-», если не знаете."),
    "Invalid year. Send a year like 1990 or «-».": (
        "Неверный год. Пришлите год, например 1990, или «-»."
    ),
    "Telegram ID or @username of this person? It is used to mention them in the group and to look up their birthday. Send «-» to skip.": (
        "Telegram ID или @username этого человека? Он нужен, чтобы упомянуть его в "
        "группе и узнать дату рождения. Пришлите «-», чтобы пропустить."
    ),
    "Could not get the birthday from Telegram, please enter it.": (
        "Не удалось получить день рождения из Telegram, введите его вручную."
    ),
    "Birthday from Telegram profile: {date}": "День рождения из профиля Telegram: {date}",
    "Invalid ID. Send a number like 123456789 or «-».": (
        "Неверный ID. Пришлите число, например 123456789, или «-»."
    ),
    "Telegram ID: {id}": "Telegram ID: {id}",
    "➕ Added {name} from {group} to contacts: {date}": (
        "➕ {name} из группы {group} добавлен(а) в контакты: {date}"
    ),
    "Could not find this username. Send the numeric Telegram ID instead, or «-».": (
        "Не удалось найти этот username. Пришлите числовой Telegram ID или «-»."
    ),
    "🆔 Telegram ID": "🆔 Telegram ID",
    "Send the Telegram ID, or «-» to remove it.": (
        "Пришлите Telegram ID или «-», чтобы удалить его."
    ),
    "Name: {name}": "Имя: {name}",
    "Relation: {relation}": "Кем приходится: {relation}",
    "New contact": "Новый контакт",
    "Send a new name.": "Пришлите новое имя.",
    "Contact not found.": "Контакт не найден.",
    "Send a new date: 12.05 or 12.05.1990.": ("Пришлите новую дату: 12.05 или 12.05.1990."),
    "Nothing to celebrate today.": "Сегодня поводов нет.",
    "Send a number of days, for example /upcoming 30.": (
        "Пришлите число дней, например /upcoming 30."
    ),
    "No events in the next {n} days.": "В ближайшие {n} дн. событий нет.",
    "Send /bindgroup in the group you want me to post in.": (
        "Отправьте /bindgroup в группе, где я должен поздравлять."
    ),
    "Only a group administrator can bind this group.": (
        "Привязать группу может только её администратор."
    ),
    "✅ This group is bound. Congratulations will be posted here.": (
        "✅ Группа привязана. Поздравления будут приходить сюда."
    ),
    "Send /unbindgroup in the group.": "Отправьте /unbindgroup в группе.",
    "This group is not bound.": "Эта группа не привязана.",
    "🔕 This group will no longer receive congratulations.": (
        "🔕 Эта группа больше не будет получать поздравления."
    ),
    "No group is bound. Add me to a group and send /bindgroup there.": (
        "Группа не привязана. Добавьте меня в группу и отправьте там /bindgroup."
    ),
    "Bound groups": "Привязанные группы",
    "Settings": "Настройки",
    "Choose the digest time:": "Выберите время дайджеста:",
    "Invalid time.": "Неверное время.",
    "Send the time in HH:MM format, for example 09:30.": (
        "Пришлите время в формате ЧЧ:ММ, например 09:30."
    ),
    "Invalid time. Send HH:MM, for example 09:30.": (
        "Неверное время. Пришлите ЧЧ:ММ, например 09:30."
    ),
    "Choose the time zone:": "Выберите часовой пояс:",
    "Unknown time zone.": "Неизвестный часовой пояс.",
    "Reminder settings:": "Настройки напоминания:",
    "Invalid value.": "Неверное значение.",
    "Choose the language:": "Выберите язык:",
    "Unknown language.": "Неизвестный язык.",
    "👋 Hi, {name}! I'm Dobby.\n\nI remember birthdays and anniversaries, "
    "send you a morning digest and congratulate people in your family group.": (
        "👋 Привет, {name}! Я Добби.\n\n"
        "Я помню дни рождения и годовщины, присылаю утренний дайджест "
        "и поздравляю в семейной группе."
    ),
    "👋 Hi! I'm Dobby.\n\nI remember birthdays and anniversaries, "
    "send you a morning digest and congratulate people in your family group.": (
        "👋 Привет! Я Добби.\n\n"
        "Я помню дни рождения и годовщины, присылаю утренний дайджест "
        "и поздравляю в семейной группе."
    ),
    "What do you want to add?": "Что хотите добавить?",
    "🎂 Birthday": "🎂 День рождения",
    "Direct messages work only after the person starts the bot.": (
        "Личные сообщения работают только после того, как человек запустит бота."
    ),
    "Subscriptions": "Подписки",
    "Choose an event to manage its channels.": ("Выберите событие, чтобы настроить каналы."),
    "📩 digest · 🎉 group · ✉️ direct": "📩 дайджест · 🎉 группа · ✉️ лично",
    "No events here.": "Здесь нет событий.",
    "Event not found.": "Событие не найдено.",
    "Updated.": "Обновлено.",
    "• <b>{name}</b> — birthday, turns {age}": (
        "• <b>{name}</b> — день рождения, исполняется {age}"
    ),
    "• <b>{name}</b> — birthday": "• <b>{name}</b> — день рождения",
    "• <b>{title}</b> — {years}": "• <b>{title}</b> — {years}",
    "• <b>{title}</b>": "• <b>{title}</b>",
    "Today": "Сегодня",
    "Have a good day!": "Хорошего дня!",
    "Make it a great day!": "Пусть день будет отличным!",
    "Don't forget to say hello!": "Не забудьте поздравить!",
    "Warm wishes to everyone!": "Тёплых слов всем!",
    "Enjoy the celebrations!": "Приятных праздников!",
    "Smiles and good mood today!": "Улыбок и хорошего настроения!",
    "🎉 <b>Happy birthday, {name}!</b>": "🎉 <b>С днём рождения, {name}!</b>",
    "🎂 {age}": "🎂 {age}",
    "🎉 <b>{title}</b>": "🎉 <b>{title}</b>",
    "🕯 <b>In memory: {title}</b>\n{years}": "🕯 <b>Памяти: {title}</b>\n{years}",
    "💍 <b>{title}: {years}</b>": "💍 <b>{title}: {years}</b>",
    "🎉 <b>{title}</b> — {years}": "🎉 <b>{title}</b> — {years}",
    "Next {n} days": "Ближайшие {n} дн.",
}

RU_PLURALS = {
    "{n} year": {0: "{n} год", 1: "{n} года", 2: "{n} лет"},
    "⏰ In {n} day": {
        0: "⏰ Через {n} день",
        1: "⏰ Через {n} дня",
        2: "⏰ Через {n} дней",
    },
}


def main() -> None:
    pot = polib.pofile(str(POT))
    po = polib.POFile()
    po.metadata = {
        "Project-Id-Version": "Dobby 0.1.0",
        "Report-Msgid-Bugs-To": "",
        "POT-Creation-Date": "",
        "PO-Revision-Date": "",
        "Last-Translator": "",
        "Language-Team": "ru",
        "Language": "ru",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Plural-Forms": (
            "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
            "n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);"
        ),
    }

    missing: list[str] = []
    for entry in pot:
        if entry.msgid_plural:
            forms = RU_PLURALS.get(entry.msgid)
            if forms is None:
                missing.append(entry.msgid)
                continue
            new = polib.POEntry(
                msgid=entry.msgid,
                msgid_plural=entry.msgid_plural,
                msgstr_plural=forms,
                occurrences=entry.occurrences,
            )
        else:
            text = RU.get(entry.msgid)
            if text is None:
                missing.append(entry.msgid)
                continue
            new = polib.POEntry(msgid=entry.msgid, msgstr=text, occurrences=entry.occurrences)
        po.append(new)

    PO.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(PO))
    po.save_as_mofile(str(PO.with_suffix(".mo")))

    if missing:
        print(f"Missing translations: {len(missing)}")
        for msgid in missing:
            print(f"  - {msgid!r}")
    print(f"Wrote {len(po)} entries to {PO}")


if __name__ == "__main__":
    main()
