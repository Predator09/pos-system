# Offline POS System

A **local-first** point-of-sale and inventory desktop app for Windows (and other platforms with Tk). It runs entirely on your machine: **SQLite** database, no cloud API, and optional JSON backups.

## Features

- **Authentication** — Sign-in with local user accounts (PBKDF2 password hashing).
- **Dashboard** — Today’s sales and revenue, catalog size, low-stock alerts, recent checkouts, theme picker, backup status.
- **Products** — Catalog and stock (integrated with sales).
- **Sales (POS)** — Search or pick products, cart, tax totals, payment method, receipt flow.
- **Purchases & reports** — Screens present in the shell for receiving stock and exports/summaries (extend as needed).
- **Backups** — Full JSON export to `data/backups/`; daily auto-backup on login when configured.
- **Shop branding** — Header logo and shop name via settings and `app/config.py`.

## Requirements

- **Python 3.10+** (3.12+ recommended; tested with recent 3.x on Windows).
- **Tk / Tcl** — Included with the standard Windows Python installer.

## Installation

From the `pos-system` directory:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Dependencies include **ttkbootstrap**, **Pillow**, **reportlab**, **openpyxl**, and **python-dateutil** (see `requirements.txt`).

## Run

```bash
python run.py
```

On first launch the app creates the database under `data/` and applies migrations. Sign in with your user (see below).

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

- Shop display name, currency symbol, tax rate  
- Window title and default size  
- Default UI theme name (`THEME`, used with ttkbootstrap)  
- Database path (`DATABASE_PATH`, relative to the working directory — usually `data/pos_system.db`)

Persisted theme choice is stored under `data/app_settings.json` (via `app_settings` service).

## Project layout

| Path | Purpose |
|------|---------|
| `run.py` | Application entry point |
| `app/config.py` | App and business constants |
| `app/database/` | SQLite connection, migrations, sync helpers |
| `app/services/` | Auth, products, sales, backup, settings |
| `app/ui/` | Screens, dialogs, widgets |
| `app/ui/windows/main_window.py` | Main window, login → shell navigation |
| `data/` | Database, backups, shop assets (created at runtime) |
| `scripts/verify_home_init.py` | Optional smoke test for dashboard init |

## Development notes

- Run from the **`pos-system`** directory so paths like `data/pos_system.db` resolve correctly.
- The Home screen theme control uses the **stdlib** `tkinter.ttk.Combobox` for the theme list to avoid a known fragile path in some environments right after the login view is torn down.
- UI is built with **ttkbootstrap** on top of **Tkinter**.

## License

Use and modify according to your project’s license (not specified in this repository).
