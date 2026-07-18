"""Restaurant model."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Restaurant(Base, TimestampMixin):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    cuisine_id: Mapped[int] = mapped_column(ForeignKey("cuisines.id"), nullable=False, index=True)
    secondary_cuisine_id: Mapped[int] = mapped_column(
        ForeignKey("cuisines.id"), nullable=True
    )

    onboarding_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    price_tier: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 budget .. 4 premium
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)  # e.g. 0.20
    base_prep_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)  # 1.0 - 5.0
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    closed_date: Mapped[date] = mapped_column(Date, nullable=True)

    city = relationship("City", back_populates="restaurants")
    cuisine = relationship(
        "Cuisine", back_populates="restaurants", foreign_keys=[cuisine_id]
    )
    secondary_cuisine = relationship("Cuisine", foreign_keys=[secondary_cuisine_id])
    orders = relationship("Order", back_populates="restaurant")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Restaurant {self.id} {self.name}>"
