"""Marketing analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics import marketing as mk
from app.analytics.filters import Filters
from app.analytics.util import to_native
from app.api.deps import get_current_user, get_filters
from app.core.database import get_db
from app.models import User

router = APIRouter()


@router.get("/coupons")
def coupons(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(mk.coupon_effectiveness(db, f))


@router.get("/efficiency")
def efficiency(f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(mk.marketing_efficiency(db, f))
