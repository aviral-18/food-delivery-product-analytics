"""
ORM model registry.

Importing this package imports every model so that `Base.metadata` is fully
populated (needed for `create_all`, migrations, and relationship resolution).
"""
from app.models.auth import AuditLog, User
from app.models.catalog import Cuisine
from app.models.customer import Customer
from app.models.delivery import DeliveryPartner
from app.models.geography import City
from app.models.marketing import Coupon, MarketingSpend
from app.models.order import Order, OrderItem
from app.models.restaurant import Restaurant

__all__ = [
    "City",
    "Cuisine",
    "Customer",
    "Restaurant",
    "DeliveryPartner",
    "Coupon",
    "MarketingSpend",
    "Order",
    "OrderItem",
    "User",
    "AuditLog",
]
