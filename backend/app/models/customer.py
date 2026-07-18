"""Customer model."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    gender: Mapped[str] = mapped_column(String(10), nullable=True)
    birth_year: Mapped[int] = mapped_column(Integer, nullable=True)

    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    signup_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    acquisition_channel: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    device: Mapped[str] = mapped_column(String(10), nullable=False)

    # Lifecycle. `is_active` is a stored flag; the analytics engine also derives
    # churn dynamically from recency, but we persist a churn_date for admin views.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    churn_date: Mapped[date] = mapped_column(Date, nullable=True)

    city = relationship("City", back_populates="customers")
    orders = relationship("Order", back_populates="customer")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Customer {self.id} {self.full_name}>"
