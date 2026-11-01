from __future__ import annotations

import gettext as _gettext
from functools import lru_cache
from pathlib import Path
from typing import Any

import polib

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
SUPPORTED_LOCALES = ("ru", "en")
LOCALE_NAMES = {"ru": "Русский", "en": "English"}
DEFAULT_LOCALE = "ru"


def compile_catalogs(force: bool = False) -> None:
    """Compile every .po next to its .mo when the source is newer."""
    for po_path in LOCALES_DIR.glob("*/LC_MESSAGES/*.po"):
        mo_path = po_path.with_suffix(".mo")
        if force or not mo_path.exists() or po_path.stat().st_mtime > mo_path.stat().st_mtime:
            try:
                polib.pofile(str(po_path)).save_as_mofile(str(mo_path))
            except OSError:  # read-only install: fall back to the existing .mo / msgid
                continue


@lru_cache(maxsize=16)
def _translation(locale: str) -> _gettext.NullTranslations:
    try:
        return _gettext.translation(
            "dobby", localedir=str(LOCALES_DIR), languages=[locale], fallback=True
        )
    except Exception:  # pragma: no cover - defensive
        return _gettext.NullTranslations()


class Translator:
    def __init__(self, locale: str) -> None:
        self.locale = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
        self._catalog = _translation(self.locale)

    def gettext(self, msgid: str, **kwargs: Any) -> str:
        text = self._catalog.gettext(msgid)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text

    def ngettext(self, singular: str, plural: str, n: int, **kwargs: Any) -> str:
        text = self._catalog.ngettext(singular, plural, n)
        try:
            return text.format(n=n, **kwargs)
        except (KeyError, IndexError):
            return text

    @property
    def _(self):
        return self.gettext


@lru_cache(maxsize=16)
def get_translator(locale: str) -> Translator:
    return Translator(locale)


def normalize_locale(locale: str | None) -> str:
    return locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
