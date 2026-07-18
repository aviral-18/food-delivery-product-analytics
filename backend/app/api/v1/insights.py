"""AI Insights endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics import insights as ins
from app.analytics.filters import Filters
from app.analytics.util import to_native
from app.api.deps import get_current_user, get_filters
from app.core.database import get_db
from app.models import User

router = APIRouter()


@router.get("/pages")
def pages(_: User = Depends(get_current_user)):
    return {"pages": ins.available_pages()}


@router.get("")
def insights(page: str = Query("executive"), f: Filters = Depends(get_filters),
             db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(ins.generate_insights(db, f, page))
