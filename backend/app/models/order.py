"""
Order fact table + order line items.

`orders` is the analytical grain of the platform. To keep the SQL Explorer and
the analytics engine fast and legible, several derived values are *pre-computed*
at generation time and stored as columns:

  * financials (commission, delivery cost, gross/net revenue, contribution margin)
  * time context (order_date, day_part, is_weekend, is_festival)
  * SLA context (is_late)
  * lifecycle context (is_first_order)

This mirrors how a real analytics warehouse maintains a curated `fct_orders`
model rather than recomputing unit economics on every query.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # ---- Foreign keys ----
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    delivery_partner_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_partners.id"), nullable=True, index=True
    )
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"), nullable=True, index=True)

    # ---- Time ----
    order_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    day_part: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_festival: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    festival_name: Mapped[str] = mapped_column(String(60), nullable=True)
    weather: Mapped[str] = mapped_column(String(20), nullable=False)

    # ---- Status / lifecycle ----
    status: Mapped[str] = mapped_column(String(15), nullable=False, index=True)  # delivered | cancelled
    is_first_order: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # ---- Basket ----
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # GMV / food value

    # ---- Charges ----
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    platform_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    taxes: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    tip: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # customer pays

    # ---- Unit economics (pre-computed) ----
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    commission_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    delivery_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    payment_gateway_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    support_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    gross_revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    contribution_margin: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # ---- Delivery SLA ----
    distance_km: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    promised_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    prep_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    delivery_minutes: Mapped[int] = mapped_column(Integer, nullable=True)  # order -> delivered
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    # ---- Experience ----
    restaurant_rating: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-5
    delivery_rating: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-5

    # ---- Cancellation / refund ----
    cancellation_reason: Mapped[str] = mapped_column(String(40), nullable=True)
    is_refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    refund_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    refund_reason: Mapped[str] = mapped_column(String(40), nullable=True)

    # relationships
    customer = relationship("Customer", back_populates="orders")
    restaurant = relationship("Restaurant", back_populates="orders")
    city = relationship("City", back_populates="orders")
    delivery_partner = relationship("DeliveryPartner", back_populates="orders")
    coupon = relationship("Coupon", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        # Composite indexes that mirror the analytics engine's common GROUP BYs.
        Index("ix_orders_date_status", "order_date", "status"),
        Index("ix_orders_customer_date", "customer_id", "order_date"),
        Index("ix_orders_city_date", "city_id", "order_date"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Order {self.id} {self.status} ₹{self.total_amount}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="items")
