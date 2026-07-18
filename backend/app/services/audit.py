"""Audit-log service."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_action(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity: str | None = None,
    entity_id: str | None = None,
    ip_address: str | None = None,
    detail: str | None = None,
) -> None:
    """Append an audit record. Best-effort: never breaks the request path."""
    try:
        db.add(AuditLog(
            user_id=user_id, action=action, entity=entity, entity_id=entity_id,
            ip_address=ip_address, detail=detail, created_at=datetime.now(timezone.utc),
        ))
        db.commit()
    except Exception:
        db.rollback()
