"""SQL Explorer endpoints (view canonical SQL, run curated or ad-hoc queries)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.analytics import registry as reg
from app.analytics.filters import Filters
from app.analytics.util import to_native
from app.api.deps import get_current_user, get_filters, require_roles
from app.core.constants import UserRole
from app.core.database import get_db
from app.models import User
from app.schemas.analytics import SqlExecuteRequest
from app.services.audit import log_action

router = APIRouter()


@router.get("/queries")
def list_queries(_: User = Depends(get_current_user)):
    """The catalogue of metric SQL with business context (living documentation)."""
    return {"queries": reg.list_queries()}


@router.get("/queries/{key}")
def run_catalog_query(key: str, limit: int = Query(200, ge=1, le=2000),
                      f: Filters = Depends(get_filters), db: Session = Depends(get_db),
                      _: User = Depends(get_current_user)):
    try:
        return to_native(reg.run_catalog_query(db, key, f, limit=limit))
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown query key: {key}")


@router.post("/execute")
def execute(payload: SqlExecuteRequest, request: Request, db: Session = Depends(get_db),
            user: User = Depends(require_roles(UserRole.ADMIN.value, UserRole.PRODUCT_ANALYST.value))):
    """Ad-hoc read-only SELECT execution (analyst/admin only)."""
    try:
        result = reg.safe_execute(db, payload.sql, limit=payload.limit)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    log_action(db, user_id=user.id, action="sql_execute", entity="sql",
               ip_address=request.client.host if request.client else None,
               detail=payload.sql[:500])
    return to_native(result)
