"""Admin panel endpoints: user management, audit logs, entity browsing, coupons."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.constants import UserRole
from app.core.database import get_db
from app.core.security import hash_password
from app.models import AuditLog, City, Coupon, Customer, DeliveryPartner, Order, Restaurant, User
from app.schemas.analytics import UserCreate, UserUpdate
from app.schemas.auth import UserOut
from app.services.audit import log_action

router = APIRouter()

_ADMIN = require_roles(UserRole.ADMIN.value)
_STAFF = require_roles(UserRole.ADMIN.value, UserRole.PRODUCT_MANAGER.value, UserRole.PRODUCT_ANALYST.value)


# --------------------------------------------------------------------------- #
#  System overview
# --------------------------------------------------------------------------- #
@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(_STAFF)):
    return {
        "counts": {
            "users": db.query(func.count(User.id)).scalar(),
            "customers": db.query(func.count(Customer.id)).scalar(),
            "restaurants": db.query(func.count(Restaurant.id)).scalar(),
            "delivery_partners": db.query(func.count(DeliveryPartner.id)).scalar(),
            "cities": db.query(func.count(City.id)).scalar(),
            "orders": db.query(func.count(Order.id)).scalar(),
            "coupons": db.query(func.count(Coupon.id)).scalar(),
            "audit_logs": db.query(func.count(AuditLog.id)).scalar(),
        },
        "active_customers": db.query(func.count(Customer.id)).filter(Customer.is_active.is_(True)).scalar(),
        "active_restaurants": db.query(func.count(Restaurant.id)).filter(Restaurant.is_active.is_(True)).scalar(),
    }


# --------------------------------------------------------------------------- #
#  User management (admin only)
# --------------------------------------------------------------------------- #
@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(_ADMIN)):
    return db.query(User).order_by(User.id).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db), admin: User = Depends(_ADMIN)):
    if payload.role not in {r.value for r in UserRole}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid role")
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
    user = User(
        email=payload.email.lower(), full_name=payload.full_name, role=payload.role,
        hashed_password=hash_password(payload.password), is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, user_id=admin.id, action="create_user", entity="user", entity_id=str(user.id),
               ip_address=request.client.host if request.client else None)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, request: Request, db: Session = Depends(get_db), admin: User = Depends(_ADMIN)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        if payload.role not in {r.value for r in UserRole}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid role")
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    log_action(db, user_id=admin.id, action="update_user", entity="user", entity_id=str(user.id),
               ip_address=request.client.host if request.client else None)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(_ADMIN)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot delete your own account")
    db.delete(user)
    db.commit()
    log_action(db, user_id=admin.id, action="delete_user", entity="user", entity_id=str(user_id),
               ip_address=request.client.host if request.client else None)


# --------------------------------------------------------------------------- #
#  Audit logs
# --------------------------------------------------------------------------- #
@router.get("/audit-logs")
def audit_logs(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
               db: Session = Depends(get_db), _: User = Depends(_ADMIN)):
    total = db.query(func.count(AuditLog.id)).scalar()
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "logs": [{
            "id": a.id, "user_id": a.user_id, "action": a.action, "entity": a.entity,
            "entity_id": a.entity_id, "ip_address": a.ip_address, "detail": a.detail,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in rows],
    }


# --------------------------------------------------------------------------- #
#  Entity browsing (paginated)
# --------------------------------------------------------------------------- #
@router.get("/customers")
def list_customers(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                   city_id: int | None = Query(None), db: Session = Depends(get_db), _: User = Depends(_STAFF)):
    q = db.query(Customer)
    if city_id:
        q = q.filter(Customer.city_id == city_id)
    total = q.count()
    rows = q.order_by(Customer.id).offset(offset).limit(limit).all()
    return {"total": total, "items": [{
        "id": c.id, "full_name": c.full_name, "email": c.email, "city_id": c.city_id,
        "signup_date": str(c.signup_date), "acquisition_channel": c.acquisition_channel,
        "is_active": c.is_active,
    } for c in rows]}


@router.get("/restaurants")
def list_restaurants(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                     city_id: int | None = Query(None), db: Session = Depends(get_db), _: User = Depends(_STAFF)):
    q = db.query(Restaurant)
    if city_id:
        q = q.filter(Restaurant.city_id == city_id)
    total = q.count()
    rows = q.order_by(Restaurant.id).offset(offset).limit(limit).all()
    return {"total": total, "items": [{
        "id": r.id, "name": r.name, "city_id": r.city_id, "cuisine_id": r.cuisine_id,
        "price_tier": r.price_tier, "baseline_rating": float(r.baseline_rating), "is_active": r.is_active,
    } for r in rows]}


@router.get("/coupons")
def list_coupons(db: Session = Depends(get_db), _: User = Depends(_STAFF)):
    rows = db.query(Coupon).order_by(Coupon.start_date).all()
    return {"items": [{
        "id": c.id, "code": c.code, "campaign_name": c.campaign_name, "discount_type": c.discount_type,
        "discount_value": float(c.discount_value), "target_segment": c.target_segment,
        "start_date": str(c.start_date), "end_date": str(c.end_date), "is_active": c.is_active,
    } for c in rows]}


@router.patch("/coupons/{coupon_id}/toggle")
def toggle_coupon(coupon_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(_ADMIN)):
    c = db.get(Coupon, coupon_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Coupon not found")
    c.is_active = not c.is_active
    db.commit()
    log_action(db, user_id=admin.id, action="toggle_coupon", entity="coupon", entity_id=str(coupon_id),
               ip_address=request.client.host if request.client else None, detail=f"is_active={c.is_active}")
    return {"id": c.id, "is_active": c.is_active}
