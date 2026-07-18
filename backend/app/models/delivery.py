"""Delivery partner model."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class DeliveryPartner(Base, TimestampMixin):
    __tablename__ = "delivery_partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    join_date: Mapped[date] = mapped_column(Date, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    shift: Mapped[str] = mapped_column(String(20), nullable=False)
    baseline_rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    # Latent reliability score (0-1): how consistently this partner beats ETA.
    # Used by the generator; exposed nowhere as ground truth to analytics.
    reliability: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    city = relationship("City", back_populates="partners")
    orders = relationship("Order", back_populates="delivery_partner")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DeliveryPartner {self.id} {self.full_name}>"
