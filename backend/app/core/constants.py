"""
Domain constants and controlled vocabularies.

These enums are the canonical allowed values for the categorical columns in the
data model. They are used by the synthetic data generator, the ORM layer, and
the analytics engine so that every layer speaks the same vocabulary. We store
the string *values* in Postgres (not native ENUM types) to keep migrations and
ad-hoc SQL in the SQL Explorer simple and portable.
"""
from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """String-valued enum whose members render as their value in SQL / JSON."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


# --------------------------------------------------------------------------- #
#  Auth
# --------------------------------------------------------------------------- #
class UserRole(StrEnum):
    ADMIN = "admin"
    PRODUCT_MANAGER = "product_manager"
    PRODUCT_ANALYST = "product_analyst"


# --------------------------------------------------------------------------- #
#  Orders
# --------------------------------------------------------------------------- #
class OrderStatus(StrEnum):
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    UPI = "upi"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    WALLET = "wallet"
    NET_BANKING = "net_banking"
    COD = "cod"


class DayPart(StrEnum):
    BREAKFAST = "breakfast"   # 06:00 - 10:59
    LUNCH = "lunch"           # 11:00 - 15:59
    SNACKS = "snacks"         # 16:00 - 18:59
    DINNER = "dinner"         # 19:00 - 22:59
    LATE_NIGHT = "late_night"  # 23:00 - 05:59


class Weather(StrEnum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    EXTREME_HEAT = "extreme_heat"
    FOG = "fog"


class CancellationReason(StrEnum):
    RESTAURANT_UNAVAILABLE = "restaurant_unavailable"
    ITEM_OUT_OF_STOCK = "item_out_of_stock"
    LONG_WAIT = "long_wait"
    CUSTOMER_CHANGED_MIND = "customer_changed_mind"
    NO_DELIVERY_PARTNER = "no_delivery_partner"
    ADDRESS_ISSUE = "address_issue"
    PAYMENT_FAILED = "payment_failed"


class RefundReason(StrEnum):
    LATE_DELIVERY = "late_delivery"
    WRONG_ITEM = "wrong_item"
    MISSING_ITEM = "missing_item"
    FOOD_QUALITY = "food_quality"
    SPILLED_DAMAGED = "spilled_damaged"
    NEVER_DELIVERED = "never_delivered"


# --------------------------------------------------------------------------- #
#  Customer
# --------------------------------------------------------------------------- #
class AcquisitionChannel(StrEnum):
    ORGANIC = "organic"
    PAID_SEARCH = "paid_search"
    SOCIAL_ADS = "social_ads"
    REFERRAL = "referral"
    INFLUENCER = "influencer"
    OFFLINE_OOH = "offline_ooh"
    APP_STORE = "app_store"


class Device(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


# --------------------------------------------------------------------------- #
#  Delivery
# --------------------------------------------------------------------------- #
class VehicleType(StrEnum):
    BICYCLE = "bicycle"
    SCOOTER = "scooter"
    MOTORBIKE = "motorbike"
    CAR = "car"


class PartnerShift(StrEnum):
    MORNING = "morning"
    EVENING = "evening"
    FULL_DAY = "full_day"


# --------------------------------------------------------------------------- #
#  Marketing
# --------------------------------------------------------------------------- #
class DiscountType(StrEnum):
    FLAT = "flat"
    PERCENTAGE = "percentage"


class CouponTargetSegment(StrEnum):
    ALL = "all"
    NEW_USERS = "new_users"
    LAPSED = "lapsed"
    HIGH_VALUE = "high_value"


class MarketingChannel(StrEnum):
    GOOGLE = "google"
    META = "meta"
    TV = "tv"
    INFLUENCER = "influencer"
    OOH = "ooh"
    REFERRAL = "referral"


# --------------------------------------------------------------------------- #
#  Geography reference data — realistic Indian metro footprint
#  (name, state, region, tier, population_millions, lat, lon)
# --------------------------------------------------------------------------- #
CITIES: list[dict] = [
    {"name": "Bengaluru", "state": "Karnataka", "region": "south", "tier": 1, "population": 13.6, "lat": 12.9716, "lon": 77.5946},
    {"name": "Mumbai", "state": "Maharashtra", "region": "west", "tier": 1, "population": 20.7, "lat": 19.0760, "lon": 72.8777},
    {"name": "Delhi", "state": "Delhi", "region": "north", "tier": 1, "population": 32.9, "lat": 28.7041, "lon": 77.1025},
    {"name": "Hyderabad", "state": "Telangana", "region": "south", "tier": 1, "population": 10.5, "lat": 17.3850, "lon": 78.4867},
    {"name": "Pune", "state": "Maharashtra", "region": "west", "tier": 1, "population": 7.4, "lat": 18.5204, "lon": 73.8567},
    {"name": "Chennai", "state": "Tamil Nadu", "region": "south", "tier": 1, "population": 11.5, "lat": 13.0827, "lon": 80.2707},
    {"name": "Kolkata", "state": "West Bengal", "region": "east", "tier": 1, "population": 15.1, "lat": 22.5726, "lon": 88.3639},
    {"name": "Gurgaon", "state": "Haryana", "region": "north", "tier": 1, "population": 1.2, "lat": 28.4595, "lon": 77.0266},
    {"name": "Ahmedabad", "state": "Gujarat", "region": "west", "tier": 2, "population": 8.4, "lat": 23.0225, "lon": 72.5714},
    {"name": "Jaipur", "state": "Rajasthan", "region": "north", "tier": 2, "population": 4.0, "lat": 26.9124, "lon": 75.7873},
    {"name": "Lucknow", "state": "Uttar Pradesh", "region": "north", "tier": 2, "population": 3.6, "lat": 26.8467, "lon": 80.9462},
    {"name": "Kochi", "state": "Kerala", "region": "south", "tier": 2, "population": 2.1, "lat": 9.9312, "lon": 76.2673},
    {"name": "Indore", "state": "Madhya Pradesh", "region": "central", "tier": 2, "population": 3.3, "lat": 22.7196, "lon": 75.8577},
    {"name": "Chandigarh", "state": "Punjab", "region": "north", "tier": 2, "population": 1.2, "lat": 30.7333, "lon": 76.7794},
    {"name": "Coimbatore", "state": "Tamil Nadu", "region": "south", "tier": 3, "population": 2.5, "lat": 11.0168, "lon": 76.9558},
    {"name": "Nagpur", "state": "Maharashtra", "region": "central", "tier": 3, "population": 2.9, "lat": 21.1458, "lon": 79.0882},
]


# --------------------------------------------------------------------------- #
#  Cuisine reference data — (name, category, base_avg_price, is_veg_friendly)
# --------------------------------------------------------------------------- #
CUISINES: list[dict] = [
    {"name": "North Indian", "category": "indian", "base_price": 320, "veg_friendly": True},
    {"name": "South Indian", "category": "indian", "base_price": 180, "veg_friendly": True},
    {"name": "Biryani", "category": "indian", "base_price": 300, "veg_friendly": False},
    {"name": "Chinese", "category": "asian", "base_price": 280, "veg_friendly": True},
    {"name": "Pizza", "category": "italian", "base_price": 450, "veg_friendly": True},
    {"name": "Burgers", "category": "american", "base_price": 350, "veg_friendly": False},
    {"name": "Fast Food", "category": "american", "base_price": 250, "veg_friendly": True},
    {"name": "Rolls & Wraps", "category": "street", "base_price": 200, "veg_friendly": False},
    {"name": "Desserts", "category": "bakery", "base_price": 220, "veg_friendly": True},
    {"name": "Beverages", "category": "cafe", "base_price": 180, "veg_friendly": True},
    {"name": "Thali", "category": "indian", "base_price": 260, "veg_friendly": True},
    {"name": "Mughlai", "category": "indian", "base_price": 380, "veg_friendly": False},
    {"name": "Continental", "category": "european", "base_price": 480, "veg_friendly": True},
    {"name": "Healthy Food", "category": "health", "base_price": 400, "veg_friendly": True},
    {"name": "Seafood", "category": "coastal", "base_price": 520, "veg_friendly": False},
    {"name": "Momos", "category": "asian", "base_price": 160, "veg_friendly": True},
]


# --------------------------------------------------------------------------- #
#  Festival calendar (month-day, name, demand_multiplier) — repeats each year
# --------------------------------------------------------------------------- #
FESTIVALS: list[dict] = [
    {"month": 1, "day": 1, "name": "New Year", "multiplier": 1.9},
    {"month": 1, "day": 14, "name": "Makar Sankranti", "multiplier": 1.25},
    {"month": 1, "day": 26, "name": "Republic Day", "multiplier": 1.3},
    {"month": 3, "day": 8, "name": "Holi", "multiplier": 1.35},
    {"month": 4, "day": 14, "name": "Baisakhi", "multiplier": 1.2},
    {"month": 8, "day": 15, "name": "Independence Day", "multiplier": 1.35},
    {"month": 8, "day": 30, "name": "Raksha Bandhan", "multiplier": 1.25},
    {"month": 9, "day": 7, "name": "Ganesh Chaturthi", "multiplier": 1.3},
    {"month": 10, "day": 2, "name": "Gandhi Jayanti", "multiplier": 1.15},
    {"month": 10, "day": 24, "name": "Dussehra", "multiplier": 1.4},
    {"month": 11, "day": 12, "name": "Diwali", "multiplier": 1.8},
    {"month": 12, "day": 25, "name": "Christmas", "multiplier": 1.6},
    {"month": 12, "day": 31, "name": "New Year Eve", "multiplier": 2.0},
]


# --------------------------------------------------------------------------- #
#  Financial model parameters (documented in docs/BUSINESS_ASSUMPTIONS.md)
# --------------------------------------------------------------------------- #
class Finance:
    """Simplified unit-economics parameters for the contribution-margin model."""

    PLATFORM_FEE = 6.0                 # flat platform fee charged to customer (INR)
    GST_RATE = 0.05                    # tax on food (pass-through, excluded from revenue)
    PAYMENT_GATEWAY_RATE = 0.018       # % of order total paid to payment gateway
    BASE_DELIVERY_COST_PER_KM = 9.0    # payout to delivery partner per km (INR)
    MIN_DELIVERY_PAYOUT = 25.0         # minimum partner payout per order (INR)
    SUPPORT_COST_PER_TICKET = 35.0     # avg cost per customer-support contact (INR)
    PLATFORM_FUNDED_DISCOUNT_SHARE = 0.6  # share of coupon discount funded by platform
