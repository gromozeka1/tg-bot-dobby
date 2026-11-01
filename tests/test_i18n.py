from __future__ import annotations

from pathlib import Path

import polib

from dobby.i18n import compile_catalogs, get_translator

ROOT = Path(__file__).resolve().parents[1]
POT = ROOT / "src" / "dobby" / "locales" / "dobby.pot"
PO = ROOT / "src" / "dobby" / "locales" / "ru" / "LC_MESSAGES" / "dobby.po"


def test_russian_catalog_is_complete() -> None:
    pot = polib.pofile(str(POT))
    po = polib.pofile(str(PO))
    translated = {
        entry.msgid
        for entry in po
        if entry.msgstr or any(entry.msgstr_plural.values())
    }
    missing = [entry.msgid for entry in pot if entry.msgid not in translated]
    assert missing == []


def test_translation_works() -> None:
    compile_catalogs()
    tr = get_translator("ru")
    assert tr.gettext("📅 Today") == "📅 Сегодня"
    assert tr.gettext("Saved.") == "Сохранено."
    assert "год" in tr.ngettext("{n} year", "{n} years", 1)
    assert "лет" in tr.ngettext("{n} year", "{n} years", 5)


def test_unknown_locale_falls_back_to_russian() -> None:
    tr = get_translator("xx")
    assert tr.locale == "ru"
