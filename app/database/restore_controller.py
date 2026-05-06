"""Unified restore entry point (no UI). Delegates to existing restore helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.database.db_backup import backup_database
from app.database.json_restore import restore_from_json
from app.database.restore_db import restore_database_from_backup
from app.services.app_logging import get_logger
from app.services.backup_service import BackupService


def restore_from_backup_file(backup_file, db_path, db_connection) -> dict[str, str]:
    """Restore from a ``.db`` or JSON backup, with validation and a safety snapshot when needed.

    For SQLite file restores, ``db_connection`` should be closed first (handled here for ``.db``).
    JSON restores use ``db_connection`` / ``BackupService``'s global ``db`` as implemented by
    existing helpers.
    """
    log = get_logger()
    src = Path(backup_file).resolve()
    target = Path(db_path).resolve()
    log.info("Unified restore started: src=%s target=%s", src, target)

    if not src.is_file():
        log.warning("Unified restore failed: backup file not found: %s", src)
        return {"status": "error", "message": "Backup file was not found or is not a file."}

    suffix = src.suffix.lower()

    try:
        if suffix == ".db":
            if db_connection is not None and getattr(db_connection, "connection", None) is not None:
                db_connection.close()
            restore_database_from_backup(src, target)
            log.info("Unified restore succeeded (SQLite file): %s", src)
            return {
                "status": "success",
                "message": "Database was restored from the backup file. Reconnect or restart the app if needed.",
            }

        if suffix == ".json":
            raw = json.loads(src.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                log.warning("Unified restore failed: JSON root is not an object: %s", src)
                return {"status": "error", "message": "Invalid backup: JSON root must be an object."}

            if target.is_file():
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safety = target.parent / f"{target.stem}_safety_{stamp}{target.suffix}"
                try:
                    backup_database(target, safety)
                except OSError as exc:
                    log.warning(
                        "Unified restore failed: could not create safety copy: %s (%s)", safety, exc
                    )
                    return {
                        "status": "error",
                        "message": f"Could not create a safety copy of the current database: {exc}",
                    }

            is_v1 = "version" in raw and "data" in raw and isinstance(raw.get("data"), dict)
            has_legacy_tables = "products" in raw or "sales" in raw

            if is_v1:
                try:
                    restore_from_json(src, db_connection)
                except Exception as exc:
                    log.error("Unified restore failed (versioned JSON): %s - %s", src, exc)
                    return {
                        "status": "error",
                        "message": f"Could not restore from versioned JSON backup: {exc}",
                    }
                log.info("Unified restore succeeded (versioned JSON): %s", src)
                return {
                    "status": "success",
                    "message": "Data was restored from the versioned JSON backup (key tables).",
                }

            if has_legacy_tables:
                ok = BackupService().restore_from_backup(str(src))
                if not ok:
                    log.warning("Unified restore failed (legacy JSON returned false): %s", src)
                    return {
                        "status": "error",
                        "message": "Restore from JSON backup failed. The file may be damaged or incompatible.",
                    }
                log.info("Unified restore succeeded (legacy JSON): %s", src)
                return {
                    "status": "success",
                    "message": "Database was restored from the full JSON backup.",
                }

            log.warning("Unified restore failed: unrecognized JSON format: %s", src)
            return {
                "status": "error",
                "message": "Unrecognized JSON backup format. Expected a full backup or versioned export.",
            }

        log.warning("Unified restore failed: unsupported suffix for %s", src)
        return {
            "status": "error",
            "message": "Unsupported file type. Use a .db or .json backup file.",
        }
    except json.JSONDecodeError as exc:
        log.warning("Unified restore failed: invalid JSON (%s): %s", src, exc)
        return {"status": "error", "message": f"Invalid JSON backup file: {exc}"}
    except Exception as exc:
        log.exception("Unified restore failed: %s", src)
        return {"status": "error", "message": f"Restore failed: {exc}"}
