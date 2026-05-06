"""Process-wide UI/service flags (e.g. recovery mode when the DB is missing or unhealthy)."""

from __future__ import annotations

recovery_mode: bool = False
database_status: str = "ok"


class RecoveryModeActive(Exception):
    """Raised when a mutating operation runs while ``recovery_mode`` is set."""


def set_database_health(status: str) -> None:
    """Set ``database_status`` and ``recovery_mode`` from probe result (``ok`` | ``missing`` | ``corrupted`` | ``empty``)."""
    global recovery_mode, database_status
    database_status = status
    recovery_mode = status in ("missing", "corrupted")


def is_recovery_mode() -> bool:
    return recovery_mode


def guard_writes() -> None:
    """Raise ``RecoveryModeActive`` if writes must be blocked."""
    if recovery_mode:
        raise RecoveryModeActive(
            "The database needs attention. Restore from a backup in Settings, then try again."
        )


def evaluate_recovery_action(status):
    if status == "ok":
        return {
            "action": "continue",
            "message": "System is healthy.",
        }
    if status == "missing":
        return {
            "action": "restore_required",
            "message": "Database is missing. Please restore from a backup.",
        }
    if status == "corrupted":
        return {
            "action": "restore_required",
            "message": "Database is corrupted. Please restore from a backup.",
        }
    if status == "empty":
        return {
            "action": "restore_recommended",
            "message": "Database appears empty. You may restore from a backup if data was lost.",
        }
    return {
        "action": "restore_required",
        "message": "Unknown database state. Please restore from a backup.",
    }
