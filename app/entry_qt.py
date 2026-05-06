"""Launch SmartStock (PySide6 UI)."""

from __future__ import annotations

import sys
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QDialog

from app.config import APP_NAME, MAX_SUPPORTED_DB_VERSION, is_newer_version
from app.database.connection import db
from app.database.db_health import get_database_status
from app.database.migration_runner import has_pending_migrations, run_migrations, validate_migration_state
from app.database.migrations import DatabaseMigrations
from app.services.app_logging import get_logger
from app.services.app_settings import AppSettings
from app.services.app_state import evaluate_recovery_action, set_database_health
from app.services.backup_service import BackupService
from app.services.license_service import LicenseService
from app.services.shop_context import database_path
from app.services.dialog_service import DialogService
from app.services.metadata_service import ensure_metadata_table, get_metadata, get_schema_version, set_metadata
from app.ui_qt.license_activation_dialog import LicenseActivationDialog
from app.ui_qt.main_window import MainQtWindow
from app.ui_qt.styles import get_qt_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 14))
    app.setStyleSheet(get_qt_stylesheet(AppSettings().get_appearance()))
    license_service = LicenseService()
    result = license_service.validate_license()
    if not bool(result.get("valid")):
        DialogService.error(
            APP_NAME,
            f"License validation failed: {result.get('reason', 'Unknown license error')}",
            parent=None,
        )
        dlg = LicenseActivationDialog(
            None,
            initial_reason=str(result.get("reason") or "Unknown license error"),
        )
        if dlg.exec() != QDialog.Accepted:
            return 1
        # Confirm activation result before continuing startup.
        result = license_service.validate_license()
        if not bool(result.get("valid")):
            DialogService.error(
                APP_NAME,
                f"License validation failed: {result.get('reason', 'Unknown license error')}",
                parent=None,
            )
            return 1
    status = str(result.get("status") or "valid")
    if status == "expiring_soon":
        DialogService.warning(
            APP_NAME,
            str(result.get("reason") or "License expires soon."),
            parent=None,
        )
    elif status == "expired_grace":
        DialogService.warning(
            APP_NAME,
            str(result.get("reason") or "License is in grace period."),
            parent=None,
        )
    elif status == "expired_blocked":
        DialogService.error(
            APP_NAME,
            str(result.get("reason") or "License has expired."),
            parent=None,
        )
        return 1

    db_path = database_path()
    # Truncated / empty on-disk file: treat as missing data (recovery); brand-new install has no file yet.
    db_preexisting = db_path.is_file()
    empty_db_file = db_path.is_file() and db_path.stat().st_size == 0

    migrations = DatabaseMigrations(db)
    migrations.init_database()
    db.connect()

    ensure_metadata_table()
    if get_metadata("schema_version") is None:
        if get_metadata("db_version") is None:
            set_metadata("schema_version", "0.0.0")

    current_schema_ver = get_schema_version()
    try:
        too_new = is_newer_version(current_schema_ver, MAX_SUPPORTED_DB_VERSION)
    except ValueError as exc:
        get_logger().warning("Could not parse schema_version %r: %s", current_schema_ver, exc)
        DialogService.error(
            APP_NAME,
            "Database version is corrupted or invalid.",
            parent=None,
        )
        return 1
    if too_new:
        get_logger().warning(
            "Unsupported schema_version=%r (this build supports up to %r).",
            current_schema_ver,
            MAX_SUPPORTED_DB_VERSION,
        )
        DialogService.error(
            APP_NAME,
            "This database was created by a newer version of SmartStock.",
            parent=None,
        )
        return 1

    strict_migration_sanity = str(os.getenv("SMARTSTOCK_MIGRATION_SAFE_MODE") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    try:
        validate_migration_state(stop_on_inconsistency=strict_migration_sanity)
    except RuntimeError as exc:
        get_logger().warning("Migration sanity check blocked startup (safe mode): %s", exc)
        DialogService.error(
            APP_NAME,
            "Migration metadata is inconsistent with database state.\n"
            "Startup stopped in safe mode.",
            parent=None,
        )
        return 1

    if has_pending_migrations():
        try:
            path = BackupService().create_pre_update_json_backup()
            get_logger().info("Pre-migration backup created: %s", path)
        except Exception as exc:
            get_logger().exception("Pre-migration backup failed; aborting migrations.")
            DialogService.error(
                APP_NAME,
                f"Backup before update failed. Migrations were not run.\n\n{exc}",
                parent=None,
            )
            return 1

    run_migrations()

    if empty_db_file:
        status = "missing"
    else:
        status = get_database_status(db, db_preexisting=db_preexisting)
    set_database_health(status)

    decision = evaluate_recovery_action(status)
    lg = get_logger()
    lg.info("[RECOVERY] Status: %s", status)
    lg.info("[RECOVERY] Action: %s", decision.get("action"))
    lg.info("[RECOVERY] Message: %s", decision.get("message"))
    if decision.get("action") == "restore_recommended":
        lg.warning("[RECOVERY] Restore is recommended, but startup continues without recovery mode.")

    win = MainQtWindow()
    win.show()

    def _deferred_auto_backup() -> None:
        from app.services.app_state import is_recovery_mode

        if is_recovery_mode():
            return
        try:
            BackupService().auto_backup_daily()
        except Exception as exc:
            get_logger().warning("Deferred automatic backup failed: %s", exc)

    # After the first event-loop pass so the window can paint before backup I/O.
    QTimer.singleShot(0, _deferred_auto_backup)

    return app.exec()
