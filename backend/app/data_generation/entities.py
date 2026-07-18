"""
Dimension builders: cities, cuisines, customers, restaurants, partners,
coupons, and marketing spend.

Each `build_*` returns a list of plain dicts with an explicit 1-based `id`.
Customer and restaurant dicts also carry *latent* attributes prefixed with `_`
(e.g. `_base_monthly_freq`, `_popularity`). These drive the order simulation
but are stripped before the rows are persisted — they represent the unobserved
"true" behaviour the analytics engine has to rediscover from data.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from dateutil.relativedelta import relativedelta
from faker import Faker

from app.core.constants import (
    CITIES,
    CUISINES,
    AcquisitionChannel,
    CouponTargetSegment,
    Device,
    DiscountType,
    MarketingChannel,
    PartnerShift,
    VehicleType,
)


# --------------------------------------------------------------------------- #
#  Cities & cuisines
# --------------------------------------------------------------------------- #
def build_cities(window_start: date) -> list[dict]:
    """Tier-1 cities launch first; tier-2/3 come online through the window."""
    rows: list[dict] = []
    for i, c in enumerate(CITIES, start=1):
        # Tier-1 predate the observation window; lower tiers launch later.
        if c["tier"] == 1:
            launch = window_start - relativedelta(months=18)
        elif c["tier"] == 2:
            launch = window_start - relativedelta(months=6)
        else:
            launch = window_start + relativedelta(months=3)
        rows.append(
            {
                "id": i,
                "name": c["name"],
                "state": c["state"],
                "region": c["region"],
                "tier": c["tier"],
                "population_millions": c["population"],
                "latitude": c["lat"],
                "longitude": c["lon"],
                "launch_date": launch,
                "is_active": True,
            }
        )
    return rows


def build_cuisines() -> list[dict]:
    return [
        {
            "id": i,
            "name": c["name"],
            "category": c["category"],
            "base_avg_price": float(c["base_price"]),
            "is_veg_friendly": c["veg_friendly"],
        }
        for i, c in enumerate(CUISINES, start=1)
    ]


# --------------------------------------------------------------------------- #
#  City sampling weights (population x tier bias)
# --------------------------------------------------------------------------- #
def _city_weights(cities: list[dict]) -> np.ndarray:
    w = np.array(
        [c["population_millions"] * (1.6 if c["tier"] == 1 else 1.0 if c["tier"] == 2 else 0.6) for c in cities]
    )
    return w / w.sum()


# --------------------------------------------------------------------------- #
#  Customers
# --------------------------------------------------------------------------- #
def build_customers(
    rng: np.random.Generator,
    faker: Faker,
    n: int,
    cities: list[dict],
    window_start: date,
    window_end: date,
) -> list[dict]:
    """
    Generate customers with a growth-weighted signup distribution and latent
    lifetime attributes.

    Story baked into the data: paid-acquisition share rises over time, and
    paid cohorts are less loyal -> later cohorts retain worse. This is the
    engine behind the "why is retention decreasing?" narrative.
    """
    months = max(1, (window_end.year - window_start.year) * 12 + (window_end.month - window_start.month))
    city_ids = np.array([c["id"] for c in cities])
    city_tier = {c["id"]: c["tier"] for c in cities}
    city_p = _city_weights(cities)

    # Signups grow ~2.2x from first to last month, with mild festive spikes.
    month_growth = np.linspace(1.0, 2.2, months + 1)
    month_p = month_growth / month_growth.sum()

    paid_channels = [
        AcquisitionChannel.PAID_SEARCH,
        AcquisitionChannel.SOCIAL_ADS,
        AcquisitionChannel.INFLUENCER,
        AcquisitionChannel.APP_STORE,
        AcquisitionChannel.OFFLINE_OOH,
    ]
    organic_channels = [AcquisitionChannel.ORGANIC, AcquisitionChannel.REFERRAL]
    devices = [Device.ANDROID, Device.IOS, Device.WEB]
    device_p = [0.62, 0.30, 0.08]
    genders = ["male", "female", "other"]

    rows: list[dict] = []
    for i in range(1, n + 1):
        # Signup month, then a random day inside that month.
        m = int(rng.choice(months + 1, p=month_p))
        signup_month = window_start + relativedelta(months=m)
        max_day = 27
        signup = signup_month + timedelta(days=int(rng.integers(0, max_day)))
        if signup > window_end - timedelta(days=7):
            signup = window_end - timedelta(days=7)

        # Paid share rises from 25% (month 0) to 62% (final month).
        frac = m / months
        paid_share = 0.25 + 0.37 * frac
        is_paid = rng.random() < paid_share
        if is_paid:
            channel = paid_channels[rng.choice(len(paid_channels), p=[0.30, 0.34, 0.16, 0.12, 0.08])]
        else:
            channel = organic_channels[rng.choice(len(organic_channels), p=[0.72, 0.28])]

        city_id = int(rng.choice(city_ids, p=city_p))

        # --- Latent behaviour ---
        # Loyalty: organic > paid; also decays slightly for later cohorts.
        loyalty = float(np.clip(rng.beta(2.4 if not is_paid else 1.7, 2.0) - 0.10 * frac, 0.03, 0.98))
        # Order frequency (active-month Poisson lambda): heavy-tailed.
        base_freq = float(np.clip(rng.lognormal(mean=-0.5, sigma=0.7) * (0.7 + loyalty), 0.15, 6.0))
        price_sensitivity = float(np.clip(rng.beta(2.0, 2.0) + (0.12 if city_tier[city_id] >= 2 else 0.0), 0.05, 0.98))

        rows.append(
            {
                "id": i,
                "full_name": faker.name(),
                "email": f"user{i}_{faker.user_name()[:12]}@example.com",
                "phone": faker.msisdn()[:10],
                "gender": genders[rng.choice(3, p=[0.55, 0.43, 0.02])],
                "birth_year": int(rng.integers(1972, 2006)),
                "city_id": city_id,
                "signup_date": signup,
                "acquisition_channel": str(channel),
                "device": str(devices[rng.choice(3, p=device_p)]),
                "is_active": True,   # finalised after order simulation
                "churn_date": None,
                # latent (stripped before persist)
                "_loyalty": loyalty,
                "_base_monthly_freq": base_freq,
                "_price_sensitivity": price_sensitivity,
                "_cohort_frac": frac,
            }
        )
    return rows


# --------------------------------------------------------------------------- #
#  Restaurants
# --------------------------------------------------------------------------- #
def build_restaurants(
    rng: np.random.Generator,
    faker: Faker,
    n: int,
    cities: list[dict],
    cuisines: list[dict],
    window_start: date,
    window_end: date,
) -> list[dict]:
    city_ids = np.array([c["id"] for c in cities])
    city_p = _city_weights(cities)
    city_launch = {c["id"]: c["launch_date"] for c in cities}
    cuisine_ids = np.array([c["id"] for c in cuisines])
    cuisine_price = {c["id"]: c["base_avg_price"] for c in cuisines}
    city_latlon = {c["id"]: (c["latitude"], c["longitude"]) for c in cities}

    name_prefixes = ["Spice", "Urban", "The", "Royal", "Cafe", "Kitchen", "Grand", "Tandoori",
                     "Green", "Golden", "Curry", "Biryani", "Wok", "Flame", "Coastal", "Bombay"]
    name_suffixes = ["House", "Junction", "Kitchen", "Express", "Corner", "Hub", "Bistro",
                     "Darbar", "Point", "Cafe", "Grill", "Treat", "Adda", "Story", "Court"]

    rows: list[dict] = []
    for i in range(1, n + 1):
        city_id = int(rng.choice(city_ids, p=city_p))
        # Onboarding no earlier than the city launch; ramps across the window.
        earliest = max(city_launch[city_id], window_start - relativedelta(months=12))
        span_days = max(1, (window_end - timedelta(days=14) - earliest).days)
        onboard = earliest + timedelta(days=int(rng.integers(0, span_days)))

        cuisine_id = int(rng.choice(cuisine_ids))
        secondary = int(rng.choice(cuisine_ids)) if rng.random() < 0.45 else None
        if secondary == cuisine_id:
            secondary = None

        price_tier = int(rng.choice([1, 2, 3, 4], p=[0.30, 0.38, 0.22, 0.10]))
        # Commission negotiated lower for premium/high-volume brands.
        commission = float(np.clip(rng.normal(0.215 - 0.008 * price_tier, 0.02), 0.14, 0.26))
        base_prep = int(np.clip(rng.normal(16 + 4 * price_tier, 4), 8, 45))
        rating = float(np.clip(rng.normal(4.05 + 0.05 * price_tier, 0.35), 2.6, 4.95))
        lat, lon = city_latlon[city_id]

        rows.append(
            {
                "id": i,
                "name": f"{rng.choice(name_prefixes)} {rng.choice(name_suffixes)}",
                "city_id": city_id,
                "cuisine_id": cuisine_id,
                "secondary_cuisine_id": secondary,
                "onboarding_date": onboard,
                "price_tier": price_tier,
                "commission_rate": round(commission, 4),
                "base_prep_minutes": base_prep,
                "baseline_rating": round(rating, 2),
                "latitude": round(lat + float(rng.normal(0, 0.06)), 6),
                "longitude": round(lon + float(rng.normal(0, 0.06)), 6),
                "is_active": True,
                "closed_date": None,
                # latent: popularity drives order share (Pareto-like)
                "_popularity": float(rng.pareto(1.6) + 0.2),
                # Typical *order* subtotal (INR) for this restaurant; the order
                # simulator draws around this and splits it across line items.
                "_base_price": cuisine_price[cuisine_id] * (0.85 + 0.16 * price_tier),
                "_quality": rating,
            }
        )
    return rows


# --------------------------------------------------------------------------- #
#  Delivery partners
# --------------------------------------------------------------------------- #
def build_partners(
    rng: np.random.Generator,
    faker: Faker,
    n: int,
    cities: list[dict],
    window_start: date,
    window_end: date,
) -> list[dict]:
    # Distribute partners across cities weighted by size, min 2 per city.
    weights = _city_weights(cities)
    counts = np.maximum(2, np.round(weights * (n - 2 * len(cities))).astype(int))
    # Trim/expand to hit exactly n.
    while counts.sum() > n:
        counts[np.argmax(counts)] -= 1
    while counts.sum() < n:
        counts[np.argmax(weights)] += 1

    vehicles = [VehicleType.MOTORBIKE, VehicleType.SCOOTER, VehicleType.BICYCLE, VehicleType.CAR]
    shifts = [PartnerShift.MORNING, PartnerShift.EVENING, PartnerShift.FULL_DAY]

    rows: list[dict] = []
    pid = 1
    for c, cnt in zip(cities, counts):
        for _ in range(int(cnt)):
            join = max(c["launch_date"], window_start - relativedelta(months=10))
            join = join + timedelta(days=int(rng.integers(0, 200)))
            rows.append(
                {
                    "id": pid,
                    "full_name": faker.name(),
                    "city_id": c["id"],
                    "join_date": min(join, window_end - timedelta(days=5)),
                    "vehicle_type": str(vehicles[rng.choice(4, p=[0.55, 0.28, 0.10, 0.07])]),
                    "shift": str(shifts[rng.choice(3, p=[0.30, 0.34, 0.36])]),
                    "baseline_rating": round(float(np.clip(rng.normal(4.2, 0.3), 3.0, 5.0)), 2),
                    "reliability": round(float(np.clip(rng.beta(5, 2), 0.35, 0.99)), 3),
                    "is_active": True,
                }
            )
            pid += 1
    return rows


# --------------------------------------------------------------------------- #
#  Coupons / campaigns
# --------------------------------------------------------------------------- #
def build_coupons(
    rng: np.random.Generator,
    cities: list[dict],
    window_start: date,
    window_end: date,
) -> list[dict]:
    """
    A realistic mix of campaigns spanning the window. Deliberately includes:
      * A generous Tier-2 welcome coupon in year 1 that is CUT in year 2
        (fuels the "coupon cut hurt Tier-2 retention" insight).
      * High-discount vs. modest-discount national campaigns with different
        profitability (fuels the "Campaign C: more orders, less profit" insight).
    """
    tier2_cities = [c["id"] for c in cities if c["tier"] >= 2]
    rows: list[dict] = []
    cid = 1

    def add(code, name, dtype, dval, maxd, minov, start, end, city_id, seg, budget):
        nonlocal cid
        rows.append(
            {
                "id": cid,
                "code": code,
                "campaign_name": name,
                "discount_type": str(dtype),
                "discount_value": float(dval),
                "max_discount": float(maxd),
                "min_order_value": float(minov),
                "start_date": start,
                "end_date": end,
                "city_id": city_id,
                "target_segment": str(seg),
                "budget": float(budget),
                "is_active": end >= window_end - timedelta(days=1),
            }
        )
        cid += 1

    mid = window_start + relativedelta(months=12)

    # National welcome (always on)
    add("WELCOME50", "Welcome 50% New User", DiscountType.PERCENTAGE, 50, 150, 199,
        window_start, window_end, None, CouponTargetSegment.NEW_USERS, 8_000_000)
    # Year-1 generous Tier-2 welcome (per tier-2 city), then cut in year 2.
    for c in tier2_cities:
        add(f"T2WELCOME-{c}-Y1", "Tier-2 Welcome (Generous)", DiscountType.FLAT, 120, 120, 149,
            window_start, mid, c, CouponTargetSegment.NEW_USERS, 400_000)
        add(f"T2WELCOME-{c}-Y2", "Tier-2 Welcome (Reduced)", DiscountType.FLAT, 60, 60, 199,
            mid, window_end, c, CouponTargetSegment.NEW_USERS, 250_000)

    # Quarterly national campaigns A/B/C with different economics.
    q = window_start
    labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
    li = 0
    while q < window_end:
        qend = min(q + relativedelta(months=3) - timedelta(days=1), window_end)
        label = labels[li % len(labels)]
        # Campaign C is the "high-discount, low-profit" one.
        if label == "C":
            add(f"SAVEBIG-{label}", f"Campaign {label} (Aggressive)", DiscountType.PERCENTAGE, 40, 200, 249,
                q, qend, None, CouponTargetSegment.ALL, 3_000_000)
        elif label == "A":
            add(f"TREAT-{label}", f"Campaign {label} (Efficient)", DiscountType.FLAT, 75, 75, 349,
                q, qend, None, CouponTargetSegment.ALL, 1_800_000)
        else:
            add(f"FEAST-{label}", f"Campaign {label}", DiscountType.PERCENTAGE, 25, 100, 299,
                q, qend, None, CouponTargetSegment.ALL, 1_500_000)
        q = q + relativedelta(months=3)
        li += 1

    # Weekend recurring + win-back
    add("WEEKEND40", "Weekend Flat 40", DiscountType.FLAT, 40, 40, 249,
        window_start, window_end, None, CouponTargetSegment.ALL, 2_400_000)
    add("COMEBACK", "Win-back Lapsed Users", DiscountType.PERCENTAGE, 45, 175, 199,
        window_start, window_end, None, CouponTargetSegment.LAPSED, 1_200_000)
    return rows


# --------------------------------------------------------------------------- #
#  Marketing spend (monthly x city x channel)
# --------------------------------------------------------------------------- #
def build_marketing_spend(
    rng: np.random.Generator,
    cities: list[dict],
    window_start: date,
    window_end: date,
    customer_scale: float = 1.0,
) -> list[dict]:
    # (channel, CPM in INR, click-through rate, install conversion, budget weight)
    channels = [
        (MarketingChannel.GOOGLE, 120, 0.040, 0.20, 1.4),
        (MarketingChannel.META, 90, 0.035, 0.16, 1.2),
        (MarketingChannel.TV, 250, 0.002, 0.03, 0.7),
        (MarketingChannel.INFLUENCER, 150, 0.025, 0.12, 0.9),
        (MarketingChannel.OOH, 200, 0.001, 0.02, 0.5),
    ]
    rows: list[dict] = []
    mid = 1
    month = date(window_start.year, window_start.month, 1)
    end_month = date(window_end.year, window_end.month, 1)
    month_idx = 0
    total_months = max(1, (end_month.year - month.year) * 12 + (end_month.month - month.month))
    while month <= end_month:
        growth = 1.0 + 1.4 * (month_idx / total_months)  # spend scales with the business
        for c in cities:
            if c["launch_date"] > month + relativedelta(months=1):
                continue  # city not live yet
            tier_mult = {1: 1.0, 2: 0.55, 3: 0.3}[c["tier"]]
            for channel, cpm, ctr, cvr, weight in channels:
                # Budget sized to the business (customer_scale) so CAC/ROAS stay realistic.
                base = max(1_500.0, rng.normal(3_200, 900)) * tier_mult * growth * weight * customer_scale
                spend = float(base)
                impressions = int(spend / cpm * 1000 * rng.normal(1.0, 0.05))
                clicks = int(impressions * ctr * rng.normal(1.0, 0.1))
                installs = int(clicks * cvr * rng.normal(1.0, 0.12))
                rows.append(
                    {
                        "id": mid,
                        "city_id": c["id"],
                        "month": month,
                        "channel": str(channel),
                        "spend": round(spend, 2),
                        "impressions": max(0, impressions),
                        "clicks": max(0, clicks),
                        "installs": max(0, installs),
                    }
                )
                mid += 1
        month = month + relativedelta(months=1)
        month_idx += 1
    return rows
