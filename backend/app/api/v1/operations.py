"""Operations analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics import operations as op
from app.analytics.filters import Filters
from app.analytics.util import to_native
from app.api.deps import get_current_user, get_filters
from app.core.database import get_db
from app.models import User

router = APIRouter()


@router.get("/delivery")
def delivery(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(op.delivery_operations(db, f))


@router.get("/delay-root-cause")
def delay_root_cause(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(op.delivery_delay_root_cause(db, f))


@router.get("/cancellations")
def cancellations(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(op.cancellation_analysis(db, f))


@router.get("/refunds")
def refunds(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(op.refund_analysis(db, f))


@router.get("/peak-hours")
def peak_hours(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(op.peak_hour_analytics(db, f))
