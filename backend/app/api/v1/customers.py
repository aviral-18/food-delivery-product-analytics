"""Customer analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics import customers as cu
from app.analytics.filters import Filters
from app.analytics.util import to_native
from app.api.deps import get_current_user, get_filters
from app.core.database import get_db
from app.models import User

router = APIRouter()


@router.get("/cohorts")
def cohorts(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cu.cohort_retention(db, f))


@router.get("/rfm")
def rfm(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cu.rfm_segmentation(db, f))


@router.get("/clv")
def clv(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cu.clv_analysis(db, f))


@router.get("/repeat-purchase")
def repeat_purchase(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cu.repeat_purchase(db, f))


@router.get("/order-frequency")
def order_frequency(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cu.order_frequency(db, f))


@router.get("/funnel")
def funnel(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(cu.customer_journey_funnel(db, f))
