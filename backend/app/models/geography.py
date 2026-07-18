"""City / geography model."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class City(Base, TimestampMixin):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 1 / 2 / 3
    population_millions: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    launch_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # relationships
    customers = relationship("Customer", back_populates="city")
    restaurants = relationship("Restaurant", back_populates="city")
    partners = relationship("DeliveryPartner", back_populates="city")
    orders = relationship("Order", back_populates="city")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<City {self.name} (tier {self.tier})>"
