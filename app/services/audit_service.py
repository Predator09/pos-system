from __future__ import annotations

import json
from typing import Any

from app.database.connection import db
from app.services.app_logging import log_exception


class AuditService:
    """Append-only audit events for key business/security actions."""

    def record(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: int | None = None,
        actor_user_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = json.dumps(details or {}, ensure_ascii=True, separators=(",", ":"))
        try:
            db.execute(
                """
                INSERT INTO audit_events (
                    event_type, entity_type, entity_id, actor_user_id, details_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(event_type or "").strip(),
                    str(entity_type or "").strip(),
                    int(entity_id) if entity_id is not None else None,
                    int(actor_user_id) if actor_user_id is not None else None,
                    payload,
                ),
            )
        except Exception:
            log_exception(
                "Failed to write audit event",
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_user_id=actor_user_id,
            )
