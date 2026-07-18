"""Catalog & geography analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics import catalog as cat
from app.analytics.filters import Filters
from app.analytics.util import to_native
from app.api.deps import get_current_user, get_filters
from app.core.database import get_db
from app.models import User

router = APIRouter()


@router.get("/restaurants")
def restaurants(order_by: str = Query("net_revenue"), limit: int = Query(50, ge=1, le=500),
                f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cat.restaurant_performance(db, f, limit=limit, order_by=order_by))


@router.get("/restaurants/ranking")
def restaurant_ranking(limit: int = Query(20, ge=1, le=100), f: Filters = Depends(get_filters),
                       db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cat.restaurant_ranking(db, f, limit=limit))


@router.get("/cuisines")
def cuisines(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cat.cuisine_performance(db, f))


@router.get("/cities")
def cities(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cat.city_performance(db, f))
