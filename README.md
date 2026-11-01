# Dobby — Telegram birthday & anniversary bot

Dobby remembers birthdays and anniversaries, sends a morning digest to the owner,
and posts congratulations in bound family groups. See [PLAN.md](PLAN.md) for the
design, current implementation status, and known delivery limitations.

## Install and configure (Windows)

Use Python 3.12 or newer. From the repository root in PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `BOT_TOKEN` in `.env`; optionally set `ADMIN_TG_ID` for update-handler error
reports. The default database is `data/dobby.sqlite3`. Keep `.env` private.

Run once in the foreground to verify configuration and apply migrations:

```powershell
.\.venv\Scripts\python -m dobby
```

In Telegram, send `/start` to the bot. Add it to the desired group with permission
to post messages, then send `/bindgroup` in that group as a group administrator.
Use `/help` for the bot commands.

## Run at logon and back up the database

After the foreground run succeeds, register the current Windows user's logon task
and daily 03:00 database backup task:

```powershell
.\scripts\install_task.ps1
```

The bot task launches `scripts/run_bot.ps1`, which restarts the process with
exponential backoff if it exits. The backup task uses SQLite's online backup API,
checks the resulting database, and keeps the newest 14 backups under `backups\`.
Tasks run as the current user; they do not require an elevated shell. To register
only the bot task:

```powershell
.\scripts\install_task.ps1 -SkipBackupTask
```

Run a backup manually with:

```powershell
.\.venv\Scripts\python scripts\backup_db.py
```

To change the retention count, pass `--keep N`. The bot logs to `logs\dobby.log`.
Task Scheduler can start the bot only after that Windows account logs on; configure
Windows automatic logon or start the task manually if unattended startup is needed.
If the PC is off at notification time, the bot catches up later that day.

## Update and restore

Stop the `DobbyBot` scheduled task before updating:

```powershell
Stop-ScheduledTask -TaskName DobbyBot
git pull
.\.venv\Scripts\python -m pip install -e .
Start-ScheduledTask -TaskName DobbyBot
```

To restore, stop the bot task, preserve the current `data\dobby.sqlite3`, copy a
verified `backups\dobby-*.sqlite3` backup to `data\dobby.sqlite3`, then start the task.
The application applies pending Alembic migrations when it starts.

## Development checks

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\ruff check .
.\.venv\Scripts\ruff format --check .
```

The repository currently has pre-existing files that Ruff reports as unformatted;
files changed for the current implementation pass the formatter check.
