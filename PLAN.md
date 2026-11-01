# Dobby — Telegram Birthday & Anniversary Bot — Implementation Plan

**Status:** implementation in progress · baseline approved · **Repo:** `C:\WORKDIR\TG_BOTS\tg-bot-dobby`

## 1. Goal & confirmed decisions

A personal Telegram assistant that remembers birthdays and anniversaries and congratulates people automatically.

Confirmed:

- **Stack:** Python 3.12+ + aiogram 3
- **Hosting:** this Windows PC, long polling (no domain or webhook needed)
- **Delivery:** morning DM digest to the owner **and** congratulations posted in a bound family/group chat
- **Language:** Russian by default; architecture ready for English and Polish
- **Digest time:** 09:00 Europe/Minsk (Belarus, UTC+3, no DST)
- **Birth year:** optional per contact — messages say "исполняется 35" only when known
- **Advance reminder:** global on/off switch, default on at 3 days before; days configurable
- **Groups:** start with a new test group; an existing group can be added later
- **Subscriptions:** per-event control over what goes into the digest and which people get congrats

**MVP outcome:** manage contacts, dates and subscriptions entirely from chat; every morning the bot DMs a digest and posts congrats in the group with persistent deduplication and same-day retry. Telegram delivery cannot be guaranteed exactly once across a crash after Telegram accepts a message but before its sent status is committed.

---

## 2. Telegram constraints that shape the design

| Constraint | Consequence |
|---|---|
| A bot cannot DM a person who never pressed **Start** | Direct congrats to contacts is a later opt-in feature (deep link + consent). Group posts are the workaround. |
| Bot must be a member of the group | Added manually; `/bindgroup` (group admin only) saves the chat. |
| Privacy mode is on by default | Commands still reach the bot, so `/bindgroup` works. Disable privacy via BotFather only if we later need all group messages. |
| Long polling is outbound-only | No public IP, TLS, or reverse proxy. Must run **exactly one** bot instance. |
| Token comes from @BotFather | Stored only in `.env`, never committed or logged. |

---

## 3. Architecture

```
Telegram
   ↕ long polling (aiogram 3)
Dispatcher
   ├─ middlewares: DB session · user resolve · locale (i18n) · throttling
   ├─ handlers + FSM: contacts · anniversaries · subscriptions · settings · groups
   └─ services: contacts · anniversaries · occurrences · subscriptions · notifier
                        ↓
              SQLAlchemy 2 (async) → SQLite (WAL)
                        ↑
APScheduler (60 s tick) ──→ notifier ──→ Bot API (DM digest + group posts)
config: pydantic-settings ← .env     logs: loguru → logs/
```

Single asyncio process. No Redis, Postgres, or webhook in the MVP.

**Key libraries:** `aiogram>=3.22,<4`, `SQLAlchemy>=2.0`, `alembic`, `aiosqlite`, `APScheduler>=3.11,<4`, `pydantic-settings`, `loguru`, `babel`, `tzdata` (required for `zoneinfo` on Windows), `Pillow` (phase 5), `pytest` + `pytest-asyncio` + `time-machine`, `ruff`.

> Python 3.14 is installed. If any dependency lacks a 3.14 wheel, create the venv with 3.12/3.13; the code targets 3.12+.

---

## 4. Data model (6 tables)

Dates are stored as **month/day + optional year**, not a single `DATE`, so "year unknown" and Feb 29 work naturally. All timestamps are UTC; all user-facing dates are local.

**users**
`id`, `tg_id` (unique), `username`, `first_name`, `locale` (`ru` default), `timezone` (IANA, default `Europe/Minsk`), `digest_time` (default `09:00`), `reminders_enabled` (default true), `reminder_days_before` (default `3`), `dm_enabled`, `group_enabled`, `created_at`, `updated_at`

**chats** — groups the bot may post to
`id`, `owner_id → users`, `tg_chat_id`, `title`, `type`, `is_default`, `created_at`; unique `(owner_id, tg_chat_id)`

**contacts**
`id`, `owner_id`, `full_name`, `day` (1–31), `month` (1–12), `birth_year` (nullable), `relationship`, `notes`, `target_chat_id → chats` (nullable = use default), `telegram_username` (nullable), `telegram_user_id` (nullable; used for group mentions and birthday lookup, and later for direct DM), `notify_digest`, `notify_group`, `notify_direct`, `is_active`, `created_at`, `updated_at`; index `(owner_id, month, day)`

**anniversaries**
`id`, `owner_id`, `title`, `day`, `month`, `start_year` (nullable), `kind` (`wedding` | `memorial` | `custom`), `recurring` (default true), `notes`, `target_chat_id`, `notify_digest`, `notify_group`, `notify_direct`, `is_active`, timestamps; index `(owner_id, month, day)`

**group_members** — passively collected members of bound groups
`id`, `chat_id → chats` (cascade), `tg_user_id`, `full_name`, `username`, `last_checked_at`, `imported_at`, `created_at`; unique `(chat_id, tg_user_id)`. Filled from group messages and join events; a member's birthday is requested via `getChat` (re-checked at most weekly) and, when available, the member is imported once as a contact.

**notification_log** — idempotency + audit
`id`, `owner_id`, `event_type` (`birthday` | `anniversary` | `digest` | `group_congrats` | `reminder`), `event_id` (0 for digest), `occurrence_date`, `target_chat_id` (0 for DM), `status` (`pending` | `sent` | `failed`), `telegram_message_id`, `error`, `created_at`, `sent_at`
Unique key: `(owner_id, event_type, event_id, occurrence_date, target_chat_id)` — prevents repeated sends after a committed sent status. A crash between Telegram accepting a message and the sent status commit can still cause a duplicate; Bot API sends and SQLite commits are not atomic.

Migrations via Alembic from day one (SQLite `create_all` only in tests). SQLite pragmas: `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`.

---

## 5. Bot UX

| Command | Purpose |
|---|---|
| `/start`, `/menu` | Register user, show main menu |
| `/today` | Today's birthdays and anniversaries |
| `/upcoming [days]` | Next 14 days (default), grouped by date |
| `/contacts` | Paginated contact list; tap → view / edit / delete / mute |
| `/addcontact` | Guided FSM: name → Telegram ID or @username (optional; fills birthday from the profile when Telegram shares it) → date → year → relation → target chat → Telegram ID → confirm |
| `/anniversaries` | Paginated list |
| `/addanniversary` | Guided FSM: title → date → kind → start year → recurring → target → confirm |
| `/subscriptions` | Subscriber list: per-event digest/group/direct toggles, filters, bulk mute |
| `/bindgroup` | In a group, admin only: register chat for congrats |
| `/unbindgroup` | Remove group |
| `/settings` | Timezone, digest time, reminder on/off + days, DM/group toggles, language |
| `/language` | Switch RU / EN / PL |
| `/delete_me` | Wipe all data for the user |
| `/id` | Show your numeric Telegram ID (and the chat ID in groups) |
| `@bot` mention in a bound group | Replies with today's events for that group |
| `/help`, `/cancel` | Help / abort FSM |

**Main menu (reply keyboard, Russian):** 📅 Сегодня · 👥 Контакты · 🎉 Годовщины · 🔔 Подписки · ⚙️ Настройки · ➕ Добавить

**Input rules**

- Date parser accepts `DD.MM`, `D.M.YYYY`, `DD.MM.YYYY`, `YYYY-MM-DD`, and Russian `12 мая`; validates real dates; Feb 29 allowed.
- Birth year optional; must be 1900..current year; future birth dates rejected.
- Anniversary start date may be in the past only; `start_year` optional.
- Inline confirm/cancel before every write; delete always asks "точно удалить?".
- All queries scoped by `owner_id` — users can never see each other's data.

**Message examples (Russian)**

- Digest: `Сегодня` → `🎂 Анна — день рождения, исполняется 35` / `💍 Годовщина свадьбы — 10 лет` (icon per event type, random closing phrase)
- Group: `🎉 С днём рождения, Анна! 🎂` + `Сегодня ей исполняется 35.`
- Memorial: `🕯 Памяти …` — solemn template, never "С днём рождения".
- Reminder: `⏰ Через 3 дня: день рождения Анны (15 мая).`

All strings live in gettext catalogs, never inline in handlers.

---

## 6. Subscriptions & notification routing

Every contact and every anniversary carries three independent switches:

| Switch | What it controls | Default |
|---|---|---|
| `notify_digest` | Appears in the 09:00 DM digest (and advance reminder) | on |
| `notify_group` | Congrats posted in the bound group chat | on |
| `notify_direct` | Personal DM to the contact — only if they started the bot (phase 6) | off |

**`/subscriptions` screen** — the "subscriber list":

```
🔔 Подписки
[ Все | 🎂 Дни рождения | 💍 Годовщины | 🔕 Отключённые ]

Анна — 12.05
📩 Дайджест ✅   🎉 Группа ✅   ✉️ Лично ⬜

Мама — 03.09
📩 Дайджест ✅   🎉 Группа ⬜   ✉️ Лично ⬜

[ Отключить все ДР ]  [ Включить всё ]  [ Назад ]
```

- Tap a channel button to toggle it; changes apply from the next tick, no restart.
- Filters make it easy to find muted events; bulk actions mute/unmute a whole category.
- A contact card also has a quick "🔕 Не поздравлять" action.
- **Excluding a date from the digest** = turning off `notify_digest` on that anniversary.
- **Excluding a person from DM congrats** = turning off `notify_digest` (and/or `notify_direct`) for that contact.
- If all switches are off the record stays in the lists but generates no notifications.
- Global kill switches (`dm_enabled`, `group_enabled`) remain in `/settings` and override everything.

**Advance reminder** is a separate DM (`event_type='reminder'`) sent `reminder_days_before` days before the event at the same morning tick. It has a **global on/off switch** (`reminders_enabled`); 1–30 days allowed, default 3. It respects `notify_digest`. Group reminders are not sent (DM only), so the group is not spammed.

**Routing rule per event per day:**

1. Resolve target chat: event override → user's default group → none.
2. If `notify_digest` and `dm_enabled` → add to DM digest.
3. If `notify_group` and `group_enabled` and a chat exists → post congrats.
4. If `notify_direct` and contact has `telegram_user_id` and has started the bot → DM the person (phase 6; skipped with a log entry otherwise).
5. Write one `notification_log` row per channel; the unique key dedupes.

---

## 7. Scheduling & date logic

- **One tick every 60 s** (not one job per user). For each active user: compute local now; if `local_time >= digest_time`, today's run hasn't happened, and it is still before 23:59 → run.
- **Catch-up:** if the PC was off/asleep at 09:00 and the bot starts at 14:00, it still sends that day. After 23:59 it skips (no stale congrats).
- **Idempotency:** a unique `notification_log` key identifies each channel/event/day. Persist an attempt before calling Telegram; committed `sent` rows prevent repeats and failed/pending attempts can retry.
- **Retries:** up to three attempts total, with 10 minutes between attempts, within the same day; errors are logged. Admin notification is currently limited to update-handler errors.
- **Date math:** occurrence = this year's month/day; if already past, next year. Feb 29 → **Feb 28** in non-leap years (single documented constant).
- **Age/years:** shown only when the year is known (`исполняется 35`, `10 лет`).
- **Timezones/DST:** `zoneinfo` handles DST; the wall-clock digest time stays at 09:00. Store UTC, render local. If a fixed UTC+1 (no DST shift) is really wanted, the zone becomes `Etc/GMT-1` — one config line.
- **Single instance:** Task Scheduler runs one copy; a file lock guards against accidental double-start.

**Reminder key:** `(owner, 'reminder', 0, local_date, 0)` — one reminder digest per user per day, even across restarts.

---

## 8. Localization (RU first, EN/PL later)

- `aiogram.utils.i18n` + GNU gettext: `src/dobby/locales/{ru,en,pl}/LC_MESSAGES/dobby.po` → compiled `.mo`.
- User's `locale` column; middleware resolves it per update, fallback `DEFAULT_LOCALE=ru`.
- All handler strings via `_()`, plural forms via `ngettext` (Russian needs 3 plural forms), dates via Babel (`d MMMM`, `d MMMM yyyy`).
- `/language` and a Settings button switch the locale and persist it.
- Adding a language later = drop in a `.po`, compile, add it to the list — no code changes.
- Message templates (digest, congrats, memorial, reminder) are separate functions, easy to reword without touching logic.

---

## 9. Project structure

```
tg-bot-dobby/
├─ pyproject.toml            # deps, ruff, pytest config
├─ .env.example              # BOT_TOKEN, ADMIN_TG_ID, DATABASE_URL, DEFAULT_LOCALE, DEFAULT_TZ, LOG_LEVEL
├─ .gitignore                # .env, .venv, data/, logs/, backups/
├─ README.md                 # setup + runbook
├─ PLAN.md                   # this plan
├─ alembic.ini
├─ migrations/
├─ src/dobby/
│  ├─ __main__.py            # config → db → dispatcher → scheduler → polling
│  ├─ config.py
│  ├─ logging.py
│  ├─ db/  (base.py, models.py, session.py)
│  ├─ bot/ (dispatcher.py, middlewares.py, states.py, keyboards.py, filters.py,
│  │        handlers/start.py, contacts.py, anniversaries.py, subscriptions.py,
│  │                 settings.py, groups.py, language.py, common.py)
│  ├─ services/ (contacts.py, anniversaries.py, occurrences.py, subscriptions.py,
│  │             notifier.py, templates.py)
│  ├─ locales/ (ru/, en/, pl/ — .po/.mo)
│  └─ utils/ (dates.py, parsing.py, formatting.py)
├─ tests/ (test_parsing.py, test_occurrences.py, test_subscriptions.py,
│          test_notifier.py, test_repositories.py, test_handlers.py, test_i18n.py)
├─ scripts/ (run_bot.ps1, install_task.ps1, backup_db.py, compile_locales.py)
└─ data/ logs/ backups/      # runtime, gitignored
```

---

## 10. Phases, deliverables, estimates

| Phase | Scope | Deliverable | Est. |
|---|---|---|---|
| **0. Scaffold** | pyproject, venv, config, logging, i18n skeleton with Russian catalog, lint/test setup, `.env.example`, README skeleton, first commit | `python -m dobby` starts, Russian `/start` works without a real token | 0.5 d |
| **1. Data layer** | models incl. subscription flags, Alembic migration, repositories, occurrence + date parser + tests | All date edge cases green; DB persists | 1 d |
| **2. Bot CRUD + subscriptions** | /start, menus, contacts + anniversaries CRUD with FSM, `/subscriptions` toggles, settings, group binding, language switch, pagination, scoping | Full management from chat in Russian; survives restart | 2.5 d |
| **3. Notifications** | scheduler tick, digest, group congrats, advance reminder, dedupe, catch-up, retries, /today, /upcoming | Exactly one DM + one group post per event per day; toggles honored | 1 d |
| **4. Hardening & deploy** | error handler → admin, throttling, single-instance lock, backup script, Task Scheduler + runbook, real-bot E2E | Reboot → bot returns, catch-up works, tests/ruff clean | 1 d |
| **5. Cards & stickers** | Pillow 1080×1080 card renderer (name, age, template), `sendPhoto` with text fallback; sticker `file_id` registry + `/sticker_add` | Congrat card in group; sticker send | 1–2 d |
| **6. Extras** | CSV import/export, `.ics`, multiple groups, direct-DM opt-in, EN/PL catalogs, T-3 gift reminder tuning | as needed | later |

**MVP = phases 0–4: ~6–6.5 focused development days.** Phase 5 covers the "later stickers or cards" item.

**Definition of done (MVP):** add a contact and anniversary from chat in Russian; toggle them in `/subscriptions`; bind a group; at 09:00 receive a DM digest and see group posts; committed sends are not repeated after restart; advance reminder arrives; Feb 29 and year-boundary tests pass; PC reboot brings the bot back automatically. Delivery across an uncommitted crash window is best-effort, not exactly-once.

---

## 11. Testing

- **Unit:** date parser (valid/invalid/leap, Russian month names), occurrence calc (Feb 29, Dec 31, past→next year), age/anniversary years, timezone/DST.
- **Subscriptions:** routing matrix — all flag combinations produce the expected channels; muted events produce nothing; direct DM without a Telegram ID is skipped safely.
- **Repository:** CRUD + owner scoping against a temporary SQLite file.
- **Scheduler:** fake clock verifies due user, catch-up window, after-23:59 skip, duplicate-key no-op, reminder sent exactly once per day and suppressed by the global toggle, retry/backoff.
- **Handlers:** FSM add-contact/add-anniversary and subscription toggle flows with a fake Bot session; assert DB row, confirmation text, cancel path.
- **i18n:** every key exists in `ru`; fallback works; plural forms render.
- **Manual E2E:** new test group, real token, `/bindgroup`, temporarily set digest time to +2 minutes.
- `ruff check` + `ruff format --check` + `pytest` as the local gate (GitHub Actions optional).

---

## 12. Windows deployment

1. `py -3.14 -m venv .venv` → `.venv\Scripts\pip install -e .[dev]`
2. Copy `.env.example` → `.env`, paste the BotFather token and the numeric Telegram ID.
3. `.venv\Scripts\python -m dobby` for the first run; create a test group, add the bot, send `/bindgroup`.
4. **Task Scheduler** (`scripts/install_task.ps1`): trigger *At log on*, run `scripts/run_bot.ps1` (restart loop with exponential backoff), working directory = repo root, "Start when available" enabled. Install with `.\scripts\install_task.ps1`.
5. **Logs:** `logs/dobby.log`, rotating 10 MB × 14 days; errors also DM'd to `ADMIN_TG_ID`.
6. **Backups:** daily Task Scheduler job runs `scripts/backup_db.py` (SQLite online backup API — safe with WAL) into `backups/`, checks integrity, and keeps 14 copies. The installer registers both tasks by default.
7. **Updates:** `git pull` → `pip install -e .` → restart the scheduled task.

Caveat: if the PC is off or asleep, sends happen on the next start (catch-up same day). Moving to Docker on a VPS later is straightforward — the app is stateless except for the SQLite volume.

---

## 13. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Windows PC off/asleep at digest time | Same-day catch-up; Task Scheduler "start when available"; VPS path later |
| Duplicate congrats after restart | Persisted sent status and unique `notification_log` key suppress repeat runs; a crash after Telegram accepts a send but before its sent status commits can still duplicate it |
| Two bot instances | File lock + single scheduled task |
| Token leak | `.env` gitignored; rotate via BotFather if exposed |
| Python 3.14 wheel gaps | Fall back to 3.12/3.13 venv (code targets 3.12+) |
| DOB is sensitive PII | Local SQLite only, per-owner scoping, `/delete_me`, no PII in logs |
| Group privacy mode blocks `/bindgroup` | Commands still delivered; if not, guide through BotFather `/setprivacy` |
| Telegram API limits | Far below 30 msg/s; retries with backoff |
| Feb 29 birthdays | Explicit Feb 28 policy + tests |
| Translation drift (RU/EN/PL) | Single `.po` per locale, key-existence test, RU is the source of truth |

---

## 14. Out of scope for MVP

Web admin panel, AI-generated greetings, public multi-tenant SaaS, multiple human digest subscribers, payment tiers. The `notify_*` flags and `chats` table leave room to add them later without a rewrite.

---

## 15. Deferred decisions

1. **Direct DM to contacts:** phase 6 — requires each person to press Start; `notify_direct` and `telegram_user_id` are already in the schema.
2. **Per-event reminder overrides:** global setting for the MVP; can be added later without schema changes.

---

## 16. Implementation status

The repository currently contains the package/configuration scaffold, Russian gettext catalog with English source strings, SQLAlchemy models and Alembic migrations, date/occurrence logic, CRUD and subscription chat flows, group binding, settings, account deletion, and scheduled digest/group/reminder delivery. Recent test and lint failures were fixed.

**Remaining MVP work:** operational validation with a real test bot and scheduled-task/reboot recovery on the target Windows account. The automated suite (46 tests) and Ruff lint pass; files changed during implementation pass Ruff formatting checks. The repository-wide format check still reports pre-existing formatting in other modules. Windows run/restart and Task Scheduler scripts, WAL-safe verified backups, account deletion, and the setup/runbook are implemented. Also implemented after the baseline: `/id`, Telegram ID/@username on contacts (add and edit), birthday lookup from the Telegram profile, passive group-member collection with auto-import, mention-to-reply with today's events, bot command menu for private chats only, per-type event icons, and hidden pagination for single pages. Handler/repository test coverage is focused rather than comprehensive. Phases 0–3 are implemented in substantial part; phase 4 scripts are implemented, but real-bot and reboot recovery checks remain. Card/sticker and extras remain deferred.

**Known limits:** Telegram bots cannot resolve arbitrary `@username`s or list silent group members; a birthday is only readable when the person's privacy allows the bot. `@username` works only for people already seen in a bound group.

---

## 17. Next steps

1. Run a real test-bot E2E for group binding, delivery, catch-up, and restart behavior (include: Group Privacy off for member collection, mention reply, member import).
2. Validate scheduled-task and backup recovery on the target Windows account, then expand handler/repository tests as needed (mention reply, edit Telegram ID, delete flows).
3. Optional: run `ruff format` on the remaining pre-existing files.

No public server or paid infrastructure is required.
