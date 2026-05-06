"""
Run ordered ``mNNN_*.py`` modules under :mod:`app.database.migrations`.

``current_db_version`` / checkpoint values are the **last applied migration number**
from the filename prefix (e.g. ``m001`` → ``1``), not the semver string in metadata.

Migrations should avoid :meth:`DatabaseConnection.execute` inside ``run()`` if you need a
single transaction: that helper commits after each statement. Prefer
``db_connection.connection`` / cursors for DDL batched in one transaction.

**Authoring guidelines (each ``mNNN_*.py`` migration):**

- **Idempotent** — Safe to run more than once (e.g. recovery, partial failure, or manual
  re-run). Never assume the migration has never run before.
- **Prefer ``IF NOT EXISTS``** — For new tables, indexes, or columns where SQLite allows it,
  so re-execution does not error.
- **Check schema before altering** — Query ``sqlite_master`` / ``PRAGMA table_info``, or
  catch ``OperationalError``, before ``ALTER`` / destructive steps, so older or unexpected
  DB states fail gracefully or no-op instead of breaking startup.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import re
from types import ModuleType
from typing import List, Tuple

from app.database.connection import db
from app.services.app_logging import get_logger
from app.services.metadata_service import _SCHEMA_VERSION_KEY, _TABLE, ensure_metadata_table, get_metadata

_MIGRATION_PKG = "app.database.migrations"
_CHECKPOINT_KEY = "migration_runner_applied_n"
_LAST_MIGRATION_NAME_KEY = "last_migration_name"
_MIGRATION_NUM = re.compile(r"^m(\d+)_", re.IGNORECASE)

logger = get_logger()


def _migration_num(stem: str) -> int:
    m = _MIGRATION_NUM.match(stem)
    return int(m.group(1)) if m else -1


def get_all_migrations() -> List[Tuple[str, ModuleType]]:
    """Load migration modules in migration-number order (``m001_*``, ``m002_*``, …)."""
    try:
        package = importlib.import_module(_MIGRATION_PKG)
    except Exception as exc:
        logger.warning("Could not import migration package %s: %s", _MIGRATION_PKG, exc)
        return []

    names = sorted(
        (
            module_info.name
            for module_info in pkgutil.iter_modules(package.__path__)
            if module_info.name.startswith("m")
        ),
        key=_migration_num,
    )
    if not names:
        logger.warning("No migration modules found in package %s.", _MIGRATION_PKG)
        return []

    out: List[Tuple[str, ModuleType]] = []
    for name in names:
        mod = importlib.import_module(f"{_MIGRATION_PKG}.{name}")
        out.append((name, mod))
    return out


def get_pending_migrations(current_db_version: str) -> List[Tuple[str, ModuleType]]:
    """
    Migrations not yet applied relative to *current_db_version*.

    *current_db_version* is the **numeric** id of the last applied migration
    (``\"0\"`` if none, ``\"1\"`` after ``m001_*``, etc.), **not** the ``schema_version``
    string stored in metadata (``0.0.N`` after migrations).
    """
    try:
        last_n = int((current_db_version or "0").strip() or "0")
    except ValueError:
        last_n = 0
    pending: List[Tuple[str, ModuleType]] = []
    for stem, mod in get_all_migrations():
        n = _migration_num(stem)
        if n > last_n:
            pending.append((stem, mod))
    return pending


def _run_one_in_transaction(migration_module: ModuleType, migration_name: str, migration_number: int) -> None:
    if db.connection is None:
        db.connect()
    conn = db.connection
    conn.execute("BEGIN")
    try:
        migration_module.run(db)
        conn.execute(
            f"""
            INSERT INTO {_TABLE} (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (_CHECKPOINT_KEY, str(migration_number)),
        )
        conn.execute(
            f"""
            INSERT INTO {_TABLE} (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (_LAST_MIGRATION_NAME_KEY, f"{migration_name}.py"),
        )
        conn.execute(
            f"""
            INSERT INTO {_TABLE} (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (_SCHEMA_VERSION_KEY, f"0.0.{migration_number}"),
        )
    except Exception as e:
        logger.error(f"Migration {migration_name} failed: {str(e)}", exc_info=True)
        conn.rollback()
        raise
    else:
        conn.commit()


def has_pending_migrations() -> bool:
    """True if at least one migration module has not been applied yet."""
    if db.connection is None:
        db.connect()
    ensure_metadata_table()
    raw = get_metadata(_CHECKPOINT_KEY)
    try:
        last_n = int(raw) if raw is not None and raw.strip().isdigit() else 0
    except ValueError:
        last_n = 0
    return bool(get_pending_migrations(str(last_n)))


def _table_exists(table: str) -> bool:
    row = db.fetchone(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    )
    return row is not None


def _column_exists(table: str, column: str) -> bool:
    cols = {r[1] for r in db.fetchall(f"PRAGMA table_info({table})")}
    return column in cols


def validate_migration_state(*, stop_on_inconsistency: bool | None = None) -> bool:
    """
    Basic sanity check for migration checkpoint metadata vs migration-defined markers.

    This is intentionally not a full schema diff. It validates:
    - checkpoint format / bounds vs discovered migration files
    - consistency with ``last_migration_name``
    - optional ``VALIDATION_MARKERS`` on applied migrations
    """
    if db.connection is None:
        db.connect()
    ensure_metadata_table()

    if stop_on_inconsistency is None:
        stop_on_inconsistency = str(
            os.getenv("SMARTSTOCK_MIGRATION_SAFE_MODE") or ""
        ).strip().lower() in {"1", "true", "yes", "on"}

    issues: list[str] = []

    raw = get_metadata(_CHECKPOINT_KEY)
    try:
        last_n = int(raw) if raw is not None and raw.strip().isdigit() else 0
    except ValueError:
        last_n = 0
        issues.append(f"Invalid {_CHECKPOINT_KEY!r} value: {raw!r}")

    all_migrations = get_all_migrations()
    max_n = max((_migration_num(stem) for stem, _ in all_migrations), default=0)
    if last_n > max_n:
        issues.append(
            f"Checkpoint {last_n} exceeds highest available migration number {max_n}."
        )

    last_name = (get_metadata(_LAST_MIGRATION_NAME_KEY) or "").strip()
    if last_n > 0 and not last_name:
        issues.append(f"{_LAST_MIGRATION_NAME_KEY!r} is missing for checkpoint {last_n}.")
    if last_name:
        m = _MIGRATION_NUM.match(last_name.removesuffix(".py"))
        if m is None:
            issues.append(f"Invalid {_LAST_MIGRATION_NAME_KEY!r} value: {last_name!r}")
        else:
            name_n = int(m.group(1))
            if name_n != last_n:
                issues.append(
                    f"{_LAST_MIGRATION_NAME_KEY!r} ({last_name!r}) does not match "
                    f"{_CHECKPOINT_KEY!r} ({last_n})."
                )

    # Validate markers for applied migrations only.
    for stem, mod in all_migrations:
        n = _migration_num(stem)
        if n <= 0 or n > last_n:
            continue
        markers = getattr(mod, "VALIDATION_MARKERS", None)
        if not markers:
            continue
        if not isinstance(markers, (list, tuple)):
            issues.append(f"{stem}: VALIDATION_MARKERS must be a list/tuple.")
            continue
        for marker in markers:
            if not isinstance(marker, dict):
                issues.append(f"{stem}: invalid marker (expected dict): {marker!r}")
                continue
            kind = str(marker.get("type") or "").strip().lower()
            if kind == "table_exists":
                table = str(marker.get("table") or "").strip()
                if not table:
                    issues.append(f"{stem}: table_exists marker missing 'table'.")
                    continue
                if not _table_exists(table):
                    issues.append(f"{stem}: expected table '{table}' is missing.")
            elif kind == "column_exists":
                table = str(marker.get("table") or "").strip()
                column = str(marker.get("column") or "").strip()
                if not table or not column:
                    issues.append(
                        f"{stem}: column_exists marker requires 'table' and 'column'."
                    )
                    continue
                if not _table_exists(table):
                    issues.append(
                        f"{stem}: expected table '{table}' is missing for column '{column}'."
                    )
                    continue
                if not _column_exists(table, column):
                    issues.append(f"{stem}: expected column '{table}.{column}' is missing.")
            else:
                issues.append(f"{stem}: unsupported marker type {kind!r}.")

    for issue in issues:
        logger.warning("Migration state sanity warning: %s", issue)

    if issues and stop_on_inconsistency:
        raise RuntimeError("Migration metadata/state inconsistency detected.")
    return not issues


def run_migrations(_db=None) -> None:
    """
    Apply pending migrations in order.

    Reads the last applied migration number from metadata, runs each pending
    migration in its own transaction (rollback and stop on first error), then
    updates checkpoint metadata and sets ``schema_version`` to ``0.0.<N>`` where *N*
    is the migration number from the filename (e.g. ``m001`` → ``0.0.1``). Also
    stores ``last_migration_name`` (e.g. ``m001_initial.py``) for debugging.
    """
    if db.connection is None:
        db.connect()
    ensure_metadata_table()

    raw = get_metadata(_CHECKPOINT_KEY)
    try:
        last_n = int(raw) if raw is not None and raw.strip().isdigit() else 0
    except ValueError:
        last_n = 0

    pending = get_pending_migrations(str(last_n))
    if not pending:
        logger.info("No pending migrations (checkpoint=%s).", last_n)
        return

    logger.info("Running %d pending migration(s), starting after m-number %s.", len(pending), last_n)

    for stem, mod in pending:
        migration_name = stem
        n = _migration_num(stem)
        logger.info(f"Running migration {migration_name}")
        _run_one_in_transaction(mod, migration_name, n)
        logger.info(f"Migration {migration_name} completed")
