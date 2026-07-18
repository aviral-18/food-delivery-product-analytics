"""Executive dashboard endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics import executive as ex
from app.analytics.filters import Filters
from app.analytics.util import to_native
from app.api.deps import get_current_user, get_filters
from app.core.database import get_db
from app.models import User

router = APIRouter()


@router.get("/kpis")
def kpis(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(ex.kpi_summary(db, f))


@router.get("/revenue-trend")
def revenue_trend(grain: str = Query("month"), f: Filters = Depends(get_filters),
                  db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(ex.revenue_trend(db, f, grain))


@router.get("/growth")
def growth(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(ex.growth(db, f))


@router.get("/health-index")
def health_index(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(ex.health_index(db, f))


@router.get("/overview")
def overview(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Bundled payload for the executive dashboard first paint."""
    return to_native({
        "kpis": ex.kpi_summary(db, f),
        "revenue_trend": ex.revenue_trend(db, f, "month"),
        "growth": ex.growth(db, f),
        "health_index": ex.health_index(db, f),
    })
