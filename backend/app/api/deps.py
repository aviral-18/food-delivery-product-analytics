"""
Shared API dependencies: authentication, role-based access control, and the
global-filter parser that turns query parameters into an analytics `Filters`.
"""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.analytics.filters import Filters
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

_CRED_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise _CRED_EXC
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise _CRED_EXC
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CRED_EXC
    return user


def require_roles(*roles: str):
    """Dependency factory enforcing that the current user holds one of `roles`."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of roles: {', '.join(roles)}",
            )
        return user
    return checker


# --------------------------------------------------------------------------- #
#  Global filters (query params -> Filters)
# --------------------------------------------------------------------------- #
def get_filters(
    start_date: str | None = Query(None, description="ISO date, inclusive lower bound"),
    end_date: str | None = Query(None, description="ISO date, inclusive upper bound"),
    city_ids: list[int] | None = Query(None),
    restaurant_ids: list[int] | None = Query(None),
    cuisine_ids: list[int] | None = Query(None),
    statuses: list[str] | None = Query(None),
    partner_ids: list[int] | None = Query(None),
    payment_methods: list[str] | None = Query(None),
    coupon_ids: list[int] | None = Query(None),
    channels: list[str] | None = Query(None),
    day_parts: list[str] | None = Query(None),
    is_weekend: bool | None = Query(None),
    is_festival: bool | None = Query(None),
) -> Filters:
    return Filters(
        start_date=start_date, end_date=end_date, city_ids=city_ids,
        restaurant_ids=restaurant_ids, cuisine_ids=cuisine_ids, statuses=statuses,
        partner_ids=partner_ids, payment_methods=payment_methods, coupon_ids=coupon_ids,
        channels=channels, day_parts=day_parts, is_weekend=is_weekend, is_festival=is_festival,
    )
