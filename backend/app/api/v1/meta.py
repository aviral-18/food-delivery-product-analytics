"""Reference data & filter options: cities, cuisines, coupons, partners, enums."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import constants as const
from app.core.database import get_db
from app.models import (
    City, Coupon, Cuisine, Customer, DeliveryPartner, Order, Restaurant, User,
)

router = APIRouter()


@router.get("/reference")
def reference_data(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Everything the frontend needs to label IDs and build filter dropdowns."""
    cities = db.query(City).order_by(City.tier, City.name).all()
    cuisines = db.query(Cuisine).order_by(Cuisine.name).all()
    coupons = db.query(Coupon).order_by(Coupon.campaign_name).all()
    partners = db.query(DeliveryPartner).order_by(DeliveryPartner.id).limit(500).all()
    return {
        "cities": [{"id": c.id, "name": c.name, "tier": c.tier, "region": c.region, "state": c.state} for c in cities],
        "cuisines": [{"id": c.id, "name": c.name, "category": c.category} for c in cuisines],
        "coupons": [{"id": c.id, "code": c.code, "campaign_name": c.campaign_name} for c in coupons],
        "delivery_partners": [{"id": p.id, "name": p.full_name, "city_id": p.city_id} for p in partners],
        "filter_options": {
            "statuses": [s.value for s in const.OrderStatus],
            "payment_methods": [s.value for s in const.PaymentMethod],
            "day_parts": [s.value for s in const.DayPart],
            "channels": [s.value for s in const.AcquisitionChannel],
            "weather": [s.value for s in const.Weather],
        },
    }


@router.get("/dataset-stats")
def dataset_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """High-level dataset footprint (for the admin/overview surfaces)."""
    min_d, max_d = db.query(func.min(Order.order_date), func.max(Order.order_date)).one()
    return {
        "orders": db.query(func.count(Order.id)).scalar(),
        "customers": db.query(func.count(Customer.id)).scalar(),
        "restaurants": db.query(func.count(Restaurant.id)).scalar(),
        "delivery_partners": db.query(func.count(DeliveryPartner.id)).scalar(),
        "cities": db.query(func.count(City.id)).scalar(),
        "cuisines": db.query(func.count(Cuisine.id)).scalar(),
        "coupons": db.query(func.count(Coupon.id)).scalar(),
        "date_range": {"start": str(min_d) if min_d else None, "end": str(max_d) if max_d else None},
    }
