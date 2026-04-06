# Offline POS System

A **local-first** point-of-sale and inventory desktop app for Windows (and other platforms with Qt). It runs entirely on your machine: **SQLite** database, no cloud API, and optional JSON backups.

## Features

- **Authentication** — Sign-in with local user accounts (PBKDF2 password hashing).
- **Dashboard** — Today’s sales and revenue, catalog size, low-stock alerts, recent checkouts, theme picker, backup status.
- **Products** — Catalog and stock (integrated with sales).
- **Sales (POS)** — Search or pick products, cart, payment method, receipt flow.
- **Purchases & reports** — Receiving stock, daily reports, CSV exports.
- **Backups** — Full JSON export; daily auto-backup on login when configured.
- **Shop branding** — Header logo and shop name via settings and `app/config.py`.

## Requirements

- **Python 3.10+** (3.12+ recommended; tested with recent 3.x on Windows).
- **PySide6** (see `requirements.txt`).

## Installation

From the `pos-system` directory:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Dependencies include **PySide6**, **Pillow**, **reportlab**, **openpyxl**, and **python-dateutil**.

## Run

```bash
python run.py
```

or equivalently:

```bash
python run_qt.py
```

On first launch the app creates the database under `data/` and applies migrations. Sign in with your user (see below).

Always run from the **`pos-system`** folder so `data/` paths resolve correctly.

## Default login

If you **reset the database** with the bundled script, the default account is:

| Field    | Value   |
|----------|---------|
| Username | `admin` |
| Password | `admin` |

Reset (destructive — deletes the SQLite DB and re-runs migrations):

```bash
python rebuild_db.py
```

Change the password after first use in production.

## Configuration

Edit **`app/config.py`** for:

- Shop display name, currency symbol  
- Window title and default size  
- Database path hint (`DATABASE_PATH`; live DB is under `data/shops/<shop_id>/`)

Persisted appearance (light/dark) is stored under `data/app_settings.json` (via `app_settings` service).

## Project layout

| Path | Purpose |
|------|---------|
| `run.py` / `run_qt.py` | Application entry (PySide6) |
| `app/entry_qt.py` | Qt bootstrap (migrations, stylesheet, main window) |
| `app/config.py` | App and business constants |
| `app/database/` | SQLite connection, migrations, sync helpers |
| `app/services/` | Auth, products, sales, backup, settings |
| `app/ui/` | Shared helpers and design tokens (`helpers.py`, `theme_tokens.py`) |
| `app/ui_qt/` | PySide6 screens and dialogs |
| `data/` | Database, backups, shop assets (created at runtime) |

## License

Use and modify according to your project’s license (not specified in this repository).
