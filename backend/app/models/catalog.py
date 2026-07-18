"""Cuisine catalog model."""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Cuisine(Base, TimestampMixin):
    __tablename__ = "cuisines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    base_avg_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_veg_friendly: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    restaurants = relationship(
        "Restaurant", back_populates="cuisine", foreign_keys="Restaurant.cuisine_id"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Cuisine {self.name}>"
