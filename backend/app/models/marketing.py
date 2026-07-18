"""Marketing models: coupons/campaigns and channel spend."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Coupon(Base, TimestampMixin):
    """A coupon campaign. Each order may reference at most one coupon."""

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    campaign_name: Mapped[str] = mapped_column(String(120), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # flat | percentage
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_discount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    min_order_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Nullable city_id => national campaign.
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    target_segment: Mapped[str] = mapped_column(String(20), nullable=False)
    budget: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    city = relationship("City")
    orders = relationship("Order", back_populates="coupon")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Coupon {self.code} ({self.campaign_name})>"


class MarketingSpend(Base, TimestampMixin):
    """Monthly marketing spend by city and channel (for CAC / ROAS analysis)."""

    __tablename__ = "marketing_spend"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False, index=True)  # first of month
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    spend: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False)
    installs: Mapped[int] = mapped_column(Integer, nullable=False)

    city = relationship("City")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MarketingSpend {self.channel} {self.month} city={self.city_id}>"
