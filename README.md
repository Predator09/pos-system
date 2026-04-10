# SmartStock

**SmartStock** is a **local-first** point-of-sale and inventory desktop app for Windows (and other platforms with Qt). It runs entirely on your machine: **SQLite** database, no cloud API, and optional JSON backups.

## Features

- **Authentication** — Sign-in with local user accounts (PBKDF2 password hashing).
- **Dashboard** — Today’s sales and revenue, catalog size, low-stock alerts, recent checkouts, theme picker, backup status.
- **Products** — Catalog and stock (integrated with sales).
- **Sales (POS)** — Search or pick products, cart, payment method, receipt flow.
- **Purchases & reports** — Receiving stock, daily reports, CSV exports.
- **Backups** — Full JSON export; automatic backup at most once per calendar day after login.
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

On first launch you are prompted once for the **installation code** (same value as the Inno Setup wizard; set `INSTALL_CODE_REQUIRED` in `app/config.py` and match `INSTALL_CODE` in `installer/SmartStock.iss`). Then the app creates the database and applies migrations. Sign in with your user (see below).

**Data location**

- **Running from source:** `<pos-system>/data/` (see `app/runtime_paths.py`).
- **Windows `.exe` (PyInstaller):** `%LOCALAPPDATA%\SmartStock\` — writable even when the program is installed under Program Files.

## Windows executable (optional)

One-folder build (recommended; faster startup than a single-file bundle):

```bash
pip install -r requirements.txt
pip install -r requirements-build.txt
python -m PyInstaller -y smartstock.spec
```

After a plain PyInstaller run, copy `V01_README.txt` into `dist/V01/` next to `SmartStock.exe` (or use **`powershell -ExecutionPolicy Bypass -File tools\build_v1.ps1`**, which runs PyInstaller and copies the readme automatically).

Close **SmartStock.exe** before rebuilding so `dist/V01` can be replaced. If the folder is locked, build to a fresh path: `python -m PyInstaller -y --distpath dist_built smartstock.spec` (output: `dist_built/V01/`), then delete the old `dist/V01` when nothing is using it and move or rename the new folder into `dist/`.

**Shortcut / EXE icon:** replace `assets/app_icon.png` with your square logo, then run `python tools/make_app_icon.py` and rebuild PyInstaller. The same `assets/smartstock.ico` is used by `smartstock.spec` and the Inno Setup wizard (`SetupIconFile` in `installer/SmartStock.iss`).

**If the built EXE shows “Failed to import encodings module”:** the bundle was fixed in `smartstock.spec` by turning **UPX off** (compressing Python DLLs breaks startup) and explicitly collecting the **`encodings`** package. Rebuild with a current spec. For shipping to customers, prefer building with **Python 3.12 or 3.13** (LTS-style); **3.14** is still very new and can be flaky with third-party tools.

Output: `dist/V01/` — run `SmartStock.exe`. Distribute the **whole folder** (includes `V01_README.txt`). Shop data is **not** inside that folder; it lives under `%LOCALAPPDATA%\SmartStock\` as above.

### Setup.exe with install code (Inno Setup)

1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php) (Windows).
2. Edit **`installer/SmartStock.iss`**: set `#define INSTALL_CODE` to your secret (or compile with `/DINSTALL_CODE=...`).
3. Build the app folder, then compile the installer:

```powershell
# From pos-system (builds dist\V01 then SmartStock_Setup.exe when Inno is installed)
powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1

# Or pass the code without editing the .iss file:
powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1 -InstallCode "YourSecret"
```

The wizard asks for the **installation code** before copying files. A successful install writes `%LOCALAPPDATA%\SmartStock\.install_verified` so the app does **not** ask for the code again on that PC. If you run the portable `dist\V01` folder without the installer, the app prompts once on first launch. Optional tasks: desktop icon, **start when Windows logs on** (current user). Default install directory: `%LocalAppData%\Programs\SmartStock\` (no admin prompt; correct user for startup).

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

Persisted appearance (light/dark) is stored next to the database under the app data directory (`app_settings` service).

## Project layout

| Path | Purpose |
|------|---------|
| `run.py` / `run_qt.py` | Application entry (PySide6) |
| `app/entry_qt.py` | Qt bootstrap (migrations, stylesheet, main window) |
| `app/config.py` | App and business constants (including `INSTALL_CODE_REQUIRED`) |
| `app/runtime_paths.py` | Resolves the writable data directory (dev vs frozen exe) |
| `app/database/` | SQLite connection, migrations, sync helpers |
| `app/services/` | Auth, products, sales, backup, settings |
| `app/ui/` | Shared helpers and design tokens (`helpers.py`, `theme_tokens.py`) |
| `app/ui_qt/` | PySide6 screens and dialogs |
| `installer/` | Inno Setup script + `build_installer.ps1` |
| `data/` | Database, backups, shop assets (created at runtime) |

## License

Use and modify according to your project’s license (not specified in this repository).
