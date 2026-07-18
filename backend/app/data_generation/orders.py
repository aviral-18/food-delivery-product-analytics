"""
Order simulation.

Rather than sprinkling 120k independent random rows, we simulate each customer's
*lifetime*: an activation gate, a per-month Poisson order rate, and a monthly
churn hazard that is worse for paid/late cohorts. Placing orders this way makes
retention curves, cohorts, RFM segments, CLV distributions, and repeat-purchase
rates emerge naturally — and, crucially, be *explainable*.

For each order we then derive the full order economics (commission, delivery
cost, gateway fees, refunds) and the delivery SLA (prep, travel, weather delay,
lateness) so every downstream metric has a real driver in the data.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
from dateutil.relativedelta import relativedelta

from app.core.constants import (
    CancellationReason,
    DayPart,
    Finance,
    OrderStatus,
    PaymentMethod,
    RefundReason,
    Weather,
)
from app.data_generation import seasonality as ss

# Compact per-cuisine menus (cuisine_name -> list of dishes) for order_items.
MENUS: dict[str, list[str]] = {
    "North Indian": ["Butter Chicken", "Paneer Tikka", "Dal Makhani", "Naan Basket", "Chicken Curry", "Jeera Rice"],
    "South Indian": ["Masala Dosa", "Idli Sambhar", "Filter Coffee", "Uttapam", "Vada", "Pongal"],
    "Biryani": ["Chicken Biryani", "Mutton Biryani", "Veg Biryani", "Egg Biryani", "Raita", "Kebab Platter"],
    "Chinese": ["Hakka Noodles", "Manchurian", "Fried Rice", "Chilli Paneer", "Spring Roll", "Schezwan Rice"],
    "Pizza": ["Margherita", "Farmhouse", "Pepperoni", "Garlic Bread", "Cheese Burst", "Peri Peri"],
    "Burgers": ["Chicken Burger", "Veg Burger", "Cheese Fries", "Zinger", "Double Patty", "Coke Combo"],
    "Fast Food": ["French Fries", "Nuggets", "Wrap", "Sandwich", "Nachos", "Milkshake"],
    "Rolls & Wraps": ["Chicken Roll", "Paneer Roll", "Egg Roll", "Veg Wrap", "Double Egg Roll", "Schezwan Roll"],
    "Desserts": ["Chocolate Cake", "Gulab Jamun", "Brownie", "Ice Cream", "Rasmalai", "Cheesecake"],
    "Beverages": ["Cold Coffee", "Lemonade", "Smoothie", "Iced Tea", "Mojito", "Hot Chocolate"],
    "Thali": ["Veg Thali", "Special Thali", "Rajasthani Thali", "Gujarati Thali", "Mini Thali", "Deluxe Thali"],
    "Mughlai": ["Mutton Korma", "Chicken Changezi", "Seekh Kebab", "Rumali Roti", "Nihari", "Shahi Paneer"],
    "Continental": ["Grilled Chicken", "Pasta Alfredo", "Caesar Salad", "Fish & Chips", "Steak", "Mushroom Soup"],
    "Healthy Food": ["Quinoa Bowl", "Salad Bowl", "Grilled Veg", "Protein Wrap", "Smoothie Bowl", "Poke Bowl"],
    "Seafood": ["Prawn Curry", "Fish Fry", "Crab Masala", "Grilled Fish", "Fish Curry", "Squid Rings"],
    "Momos": ["Steam Momos", "Fried Momos", "Tandoori Momos", "Schezwan Momos", "Paneer Momos", "Soup"],
}

_PAYMENTS = [
    PaymentMethod.UPI, PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD,
    PaymentMethod.WALLET, PaymentMethod.NET_BANKING, PaymentMethod.COD,
]
_PAYMENT_P = np.array([0.52, 0.14, 0.10, 0.12, 0.04, 0.08])

# Average km/h by vehicle for travel-time estimation.
_VEHICLE_SPEED = {"motorbike": 24, "scooter": 20, "bicycle": 12, "car": 22}


class OrderSimulator:
    def __init__(
        self,
        rng: np.random.Generator,
        cities: list[dict],
        customers: list[dict],
        restaurants: list[dict],
        partners: list[dict],
        coupons: list[dict],
        cuisines: list[dict],
        window_start: date,
        window_end: date,
        intensity: float = 1.9,
    ) -> None:
        self.rng = rng
        self.window_start = window_start
        self.window_end = window_end
        self.intensity = intensity

        self.city_by_id = {c["id"]: c for c in cities}
        self.cuisine_name = {c["id"]: c["name"] for c in cuisines}
        self.restaurants = restaurants
        self.customers = customers
        self.coupons = coupons

        self._index_restaurants_by_city()
        self._index_partners_by_city(partners)
        self._index_coupons()
        self._build_calendar()

        self._order_id = 0
        self._item_id = 0

    # ---- indexing helpers ------------------------------------------------- #
    def _index_restaurants_by_city(self) -> None:
        self.rest_by_city: dict[int, dict] = {}
        by_city: dict[int, list[dict]] = {}
        for r in self.restaurants:
            by_city.setdefault(r["city_id"], []).append(r)
        for city_id, rs in by_city.items():
            ids = np.array([r["id"] for r in rs])
            weights = np.array([r["_popularity"] for r in rs], dtype=float)
            weights = weights / weights.sum()
            cum = np.cumsum(weights)
            onboard = np.array([r["onboarding_date"].toordinal() for r in rs])
            prices = np.array([r["_base_price"] for r in rs])
            prep = np.array([r["base_prep_minutes"] for r in rs])
            comm = np.array([r["commission_rate"] for r in rs])
            quality = np.array([r["_quality"] for r in rs])
            cuis = np.array([r["cuisine_id"] for r in rs])
            self.rest_by_city[city_id] = {
                "ids": ids, "cum": cum, "onboard": onboard, "prices": prices,
                "prep": prep, "comm": comm, "quality": quality, "cuisine": cuis,
            }

    def _index_partners_by_city(self, partners: list[dict]) -> None:
        self.part_by_city: dict[int, dict] = {}
        by_city: dict[int, list[dict]] = {}
        for p in partners:
            by_city.setdefault(p["city_id"], []).append(p)
        for city_id, ps in by_city.items():
            self.part_by_city[city_id] = {
                "ids": np.array([p["id"] for p in ps]),
                "reliability": np.array([p["reliability"] for p in ps]),
                "speed": np.array([_VEHICLE_SPEED[p["vehicle_type"]] for p in ps]),
                "join": np.array([p["join_date"].toordinal() for p in ps]),
            }

    def _index_coupons(self) -> None:
        self.national_coupons = [c for c in self.coupons if c["city_id"] is None]
        self.city_coupons: dict[int, list[dict]] = {}
        for c in self.coupons:
            if c["city_id"] is not None:
                self.city_coupons.setdefault(c["city_id"], []).append(c)

    def _build_calendar(self) -> None:
        """Precompute daily demand weights per (year, month)."""
        self.month_days: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
        self.month_growth: dict[tuple[int, int], float] = {}
        start = date(self.window_start.year, self.window_start.month, 1)
        end = date(self.window_end.year, self.window_end.month, 1)
        total = max(1, (end.year - start.year) * 12 + (end.month - start.month))
        cur = start
        idx = 0
        while cur <= end:
            growth = 0.85 + 0.35 * (idx / total)  # mild platform maturation
            self.month_growth[(cur.year, cur.month)] = growth
            # enumerate days of this month within the window
            days: list[int] = []
            weights: list[float] = []
            d = cur
            while d.month == cur.month:
                if self.window_start <= d <= self.window_end:
                    days.append(d.toordinal())
                    weights.append(ss.day_demand_multiplier(d, growth, Weather.CLEAR))
                d += timedelta(days=1)
            if days:
                w = np.array(weights)
                self.month_days[(cur.year, cur.month)] = (np.array(days), w / w.sum())
            cur += relativedelta(months=1)
            idx += 1

    # ---- main entry ------------------------------------------------------- #
    def simulate(self) -> tuple[list[dict], list[dict], dict[int, dict]]:
        """Return (orders, order_items, customer_lifecycle_updates)."""
        orders: list[dict] = []
        items: list[dict] = []
        lifecycle: dict[int, dict] = {}
        end_month = date(self.window_end.year, self.window_end.month, 1)

        for cust in self.customers:
            city_id = cust["city_id"]
            if city_id not in self.rest_by_city:
                continue  # no restaurants in city yet
            city = self.city_by_id[city_id]
            # Effective start = later of signup and city launch.
            eff_start = max(cust["signup_date"], city["launch_date"])
            if eff_start > self.window_end - timedelta(days=3):
                continue

            loyalty = cust["_loyalty"]
            frac = cust["_cohort_frac"]

            # Activation gate: some signups never place a first order.
            activation_p = np.clip(0.62 + 0.28 * loyalty, 0.3, 0.95)
            if self.rng.random() > activation_p:
                lifecycle[cust["id"]] = {"is_active": False, "churn_date": eff_start}
                continue

            # Monthly churn hazard -> geometric active lifetime (months).
            churn_p = float(np.clip(0.40 - 0.26 * loyalty + 0.12 * frac, 0.06, 0.85))
            lifetime = int(self.rng.geometric(churn_p))

            cust_orders, cust_items, last_dt = self._simulate_customer(
                cust, city, eff_start, end_month, lifetime, orders_len=len(orders)
            )
            orders.extend(cust_orders)
            items.extend(cust_items)

            # Persisted lifecycle: churned if last order well before window end.
            if last_dt is None:
                lifecycle[cust["id"]] = {"is_active": False, "churn_date": eff_start}
            else:
                gap = (self.window_end - last_dt.date()).days
                churned = gap > 60
                lifecycle[cust["id"]] = {
                    "is_active": not churned,
                    "churn_date": (last_dt.date() + timedelta(days=45)) if churned else None,
                }
        return orders, items, lifecycle

    def _simulate_customer(self, cust, city, eff_start, end_month, lifetime, orders_len):
        orders: list[dict] = []
        items: list[dict] = []
        first_done = False
        last_dt: datetime | None = None
        month_cursor = date(eff_start.year, eff_start.month, 1)
        active_months = 0

        while month_cursor <= end_month and active_months < lifetime:
            key = (month_cursor.year, month_cursor.month)
            if key not in self.month_days:
                month_cursor += relativedelta(months=1)
                continue
            growth = self.month_growth[key]
            lam = cust["_base_monthly_freq"] * growth * self.intensity
            n = int(self.rng.poisson(lam))
            if active_months == 0 and not first_done:
                n = max(n, 1)  # activated customers place >=1 in first active month

            days_arr, day_p = self.month_days[key]
            for _ in range(n):
                ordinal = int(self.rng.choice(days_arr, p=day_p))
                d = date.fromordinal(ordinal)
                if d < eff_start or d > self.window_end:
                    continue
                is_first = not first_done
                o, its, dt = self._make_order(cust, city, d, is_first, gap_days=(d - last_dt.date()).days if last_dt else None)
                if o is None:
                    continue
                orders.append(o)
                items.extend(its)
                first_done = True
                last_dt = dt
            month_cursor += relativedelta(months=1)
            active_months += 1

        return orders, items, last_dt

    # ---- single order ----------------------------------------------------- #
    def _make_order(self, cust, city, d: date, is_first: bool, gap_days):
        rng = self.rng
        self._order_id += 1
        oid = self._order_id

        day_part = ss.sample_day_part(rng)
        dt = ss.datetime_for(rng, d, day_part)
        weather = ss.sample_weather(rng, d, city["region"])
        fest = ss.festival_for(d)

        # ----- pick restaurant (popularity-weighted, must be onboarded) -----
        rc = self.rest_by_city[city["id"]]
        ord_ordinal = d.toordinal()
        idx = None
        for _ in range(6):
            cand = int(np.searchsorted(rc["cum"], rng.random()))
            cand = min(cand, len(rc["ids"]) - 1)
            if rc["onboard"][cand] <= ord_ordinal:
                idx = cand
                break
        if idx is None:
            eligible = np.where(rc["onboard"] <= ord_ordinal)[0]
            if len(eligible) == 0:
                self._order_id -= 1
                return None, [], None
            idx = int(eligible[rng.integers(0, len(eligible))])

        restaurant_id = int(rc["ids"][idx])
        cuisine_id = int(rc["cuisine"][idx])
        base_price = float(rc["prices"][idx])
        commission_rate = float(rc["comm"][idx])
        rest_quality = float(rc["quality"][idx])
        base_prep = int(rc["prep"][idx])

        # ----- basket & items -----
        # Draw the target order value around the restaurant's typical subtotal,
        # then split it across a few line items (so AOV stays realistic and the
        # order_items always reconcile to the order subtotal).
        basket_mult = ss.DAY_PART_BASKET_MULT[day_part]
        target = float(np.clip(rng.normal(base_price, base_price * 0.30),
                               base_price * 0.35, base_price * 3.0)) * basket_mult
        item_count = int(np.clip(rng.poisson(1.2) + 1, 1, 6))
        weights = rng.dirichlet(np.ones(item_count))
        cuisine_name = self.cuisine_name.get(cuisine_id, "Fast Food")
        menu = MENUS.get(cuisine_name, MENUS["Fast Food"])
        items: list[dict] = []
        subtotal = 0.0
        for w in weights:
            qty = int(np.clip(rng.poisson(0.25) + 1, 1, 3))
            unit = round(max(30.0, target * float(w) / qty), 2)
            line = round(unit * qty, 2)
            subtotal += line
            self._item_id += 1
            items.append({
                "id": self._item_id, "order_id": oid,
                "item_name": str(rng.choice(menu)), "category": cuisine_name,
                "quantity": qty, "unit_price": unit, "line_total": line,
            })
        subtotal = round(subtotal, 2)

        # ----- surge / distance / SLA context -----
        surge = 1.0 + (0.25 if (fest or (day_part == DayPart.DINNER and d.weekday() >= 5)) else 0.0)
        distance = round(float(np.clip(rng.gamma(2.2, 1.6), 0.4, 14.0)), 2)

        # ----- cancellation decision -----
        pc = self.part_by_city.get(city["id"])
        partner_available = pc is not None and np.any(pc["join"] <= ord_ordinal)
        cancel_p = 0.045 + (0.05 if fest else 0.0) + (0.03 if weather in (Weather.STORM, Weather.RAIN) else 0.0)
        # A delivered order must have an assignable partner; without one it is
        # always cancelled (reason: no_delivery_partner).
        cancelled = (not partner_available) or (rng.random() < cancel_p)

        payment = str(self.rng_choice(_PAYMENTS, _PAYMENT_P))
        is_weekend = d.weekday() >= 5

        base = {
            "id": oid, "customer_id": cust["id"], "restaurant_id": restaurant_id,
            "city_id": city["id"], "order_datetime": dt, "order_date": d,
            "day_part": str(day_part), "is_weekend": is_weekend,
            "is_festival": fest is not None, "festival_name": fest["name"] if fest else None,
            "weather": str(weather), "is_first_order": is_first, "payment_method": payment,
            "item_count": item_count, "subtotal": subtotal,
            "commission_rate": commission_rate, "distance_km": distance,
        }

        if cancelled:
            return self._finalize_cancelled(base, partner_available), items, dt

        return self._finalize_delivered(
            base, cust, city, d, dt, day_part, weather, fest, surge,
            distance, base_prep, commission_rate, rest_quality, subtotal, payment, is_first, gap_days,
        ), items, dt

    def rng_choice(self, options, p):
        return options[int(self.rng.choice(len(options), p=p))]

    # ----- cancelled order economics (no revenue) -----
    def _finalize_cancelled(self, base: dict, partner_available: bool) -> dict:
        reason = (
            CancellationReason.NO_DELIVERY_PARTNER if not partner_available
            else self.rng_choice(
                [CancellationReason.RESTAURANT_UNAVAILABLE, CancellationReason.ITEM_OUT_OF_STOCK,
                 CancellationReason.LONG_WAIT, CancellationReason.CUSTOMER_CHANGED_MIND,
                 CancellationReason.ADDRESS_ISSUE, CancellationReason.PAYMENT_FAILED],
                np.array([0.22, 0.16, 0.20, 0.24, 0.08, 0.10]),
            )
        )
        base.update({
            "status": str(OrderStatus.CANCELLED), "delivery_partner_id": None, "coupon_id": None,
            "discount_amount": 0.0, "delivery_fee": 0.0, "platform_fee": 0.0,
            "taxes": 0.0, "tip": 0.0, "total_amount": 0.0,
            "commission_amount": 0.0, "delivery_cost": 0.0, "payment_gateway_cost": 0.0,
            "support_cost": round(Finance.SUPPORT_COST_PER_TICKET * 0.4, 2),
            "gross_revenue": 0.0, "net_revenue": 0.0,
            "contribution_margin": round(-Finance.SUPPORT_COST_PER_TICKET * 0.4, 2),
            "promised_minutes": None, "prep_minutes": None, "delivery_minutes": None,
            "is_late": False, "restaurant_rating": None, "delivery_rating": None,
            "cancellation_reason": str(reason), "is_refunded": False,
            "refund_amount": 0.0, "refund_reason": None,
        })
        return base

    # ----- delivered order economics + SLA -----
    def _finalize_delivered(
        self, base, cust, city, d, dt, day_part, weather, fest, surge,
        distance, base_prep, commission_rate, rest_quality, subtotal, payment, is_first, gap_days,
    ) -> dict:
        rng = self.rng

        # ---- partner + delivery time ----
        pc = self.part_by_city[city["id"]]
        eligible = np.where(pc["join"] <= d.toordinal())[0]
        pidx = int(eligible[rng.integers(0, len(eligible))])
        partner_id = int(pc["ids"][pidx])
        reliability = float(pc["reliability"][pidx])
        speed = float(pc["speed"][pidx])

        prep = float(np.clip(rng.normal(base_prep * surge, base_prep * 0.25), 5, 90))
        travel = (distance / speed) * 60.0
        pickup_wait = float(np.clip(rng.normal(4, 2), 0, 15))
        weather_pen = ss.WEATHER_DELIVERY_PENALTY[weather]
        reliability_pen = (1.0 - reliability) * 12.0
        delivery_minutes = int(round(prep + travel + pickup_wait + weather_pen + reliability_pen))
        # Promised ETA: the app shows base prep + travel + a service buffer.
        # The buffer absorbs typical pickup wait so ~20% of orders breach SLA.
        promised = int(round(base_prep + travel + 15))
        is_late = delivery_minutes > promised

        # ---- coupon ----
        coupon_id, discount = self._apply_coupon(cust, city, d, subtotal, is_first, gap_days)

        # ---- charges ----
        free_threshold = 349.0
        delivery_fee = 0.0 if subtotal >= free_threshold else round(float(np.clip(19 + 4 * distance, 15, 70)), 2)
        platform_fee = Finance.PLATFORM_FEE
        taxes = round(subtotal * Finance.GST_RATE, 2)
        tip = round(float(rng.choice([0, 0, 0, 10, 20, 30], p=[0.55, 0.15, 0.05, 0.12, 0.08, 0.05])), 2)
        total_amount = round(subtotal - discount + delivery_fee + platform_fee + taxes + tip, 2)

        # ---- costs ----
        commission_amount = round(subtotal * commission_rate, 2)
        delivery_cost = round(max(Finance.MIN_DELIVERY_PAYOUT, distance * Finance.BASE_DELIVERY_COST_PER_KM) * surge, 2)
        gateway = 0.0 if payment == str(PaymentMethod.COD) else round(total_amount * Finance.PAYMENT_GATEWAY_RATE, 2)

        # ---- refund (delivered but a problem occurred) ----
        refund_p = 0.02 + (0.05 if is_late else 0.0) + (0.03 if rest_quality < 3.6 else 0.0)
        is_refunded = rng.random() < refund_p
        refund_amount = 0.0
        refund_reason = None
        support_cost = 0.0
        if is_refunded:
            share = float(rng.choice([0.3, 0.5, 1.0], p=[0.4, 0.35, 0.25]))
            refund_amount = round(subtotal * share, 2)
            refund_reason = str(self.rng_choice(
                [RefundReason.LATE_DELIVERY, RefundReason.WRONG_ITEM, RefundReason.MISSING_ITEM,
                 RefundReason.FOOD_QUALITY, RefundReason.SPILLED_DAMAGED, RefundReason.NEVER_DELIVERED],
                np.array([0.30, 0.15, 0.18, 0.20, 0.12, 0.05]),
            ))
            support_cost = Finance.SUPPORT_COST_PER_TICKET
        elif rng.random() < 0.03:
            support_cost = round(Finance.SUPPORT_COST_PER_TICKET * 0.5, 2)

        # ---- revenue & margin ----
        gross_revenue = round(commission_amount + delivery_fee + platform_fee, 2)
        platform_funded_discount = round(discount * Finance.PLATFORM_FUNDED_DISCOUNT_SHARE, 2)
        net_revenue = round(gross_revenue - platform_funded_discount - refund_amount, 2)
        contribution_margin = round(net_revenue - delivery_cost - gateway - support_cost, 2)

        # ---- ratings (not every order is rated) ----
        rest_rating = self._rating(rng, rest_quality, is_late, is_refunded, rate_prob=0.55)
        del_rating = self._rating(rng, 3.5 + reliability * 1.5, is_late, is_refunded, rate_prob=0.45)

        base.update({
            "status": str(OrderStatus.DELIVERED), "delivery_partner_id": partner_id, "coupon_id": coupon_id,
            "discount_amount": round(discount, 2), "delivery_fee": delivery_fee, "platform_fee": platform_fee,
            "taxes": taxes, "tip": tip, "total_amount": total_amount,
            "commission_amount": commission_amount, "delivery_cost": delivery_cost,
            "payment_gateway_cost": gateway, "support_cost": support_cost,
            "gross_revenue": gross_revenue, "net_revenue": net_revenue,
            "contribution_margin": contribution_margin,
            "promised_minutes": promised, "prep_minutes": int(round(prep)),
            "delivery_minutes": delivery_minutes, "is_late": is_late,
            "restaurant_rating": rest_rating, "delivery_rating": del_rating,
            "cancellation_reason": None, "is_refunded": is_refunded,
            "refund_amount": refund_amount, "refund_reason": refund_reason,
        })
        return base

    @staticmethod
    def _rating(rng, quality_center: float, is_late: bool, refunded: bool, rate_prob: float):
        if rng.random() > rate_prob:
            return None
        center = quality_center - (0.8 if is_late else 0.0) - (1.5 if refunded else 0.0)
        val = int(np.clip(round(rng.normal(center, 0.7)), 1, 5))
        return val

    # ---- coupon application ---------------------------------------------- #
    def _apply_coupon(self, cust, city, d: date, subtotal: float, is_first: bool, gap_days):
        candidates: list[dict] = []
        for c in self.national_coupons + self.city_coupons.get(city["id"], []):
            if not (c["start_date"] <= d <= c["end_date"]):
                continue
            if subtotal < c["min_order_value"]:
                continue
            seg = c["target_segment"]
            if seg == "new_users" and not is_first:
                continue
            if seg == "lapsed" and (gap_days is None or gap_days < 45):
                continue
            if seg == "high_value":
                continue
            candidates.append(c)
        if not candidates:
            return None, 0.0

        # New users almost always redeem the best welcome offer; others are
        # price-sensitivity driven.
        use_p = 0.9 if is_first else (0.15 + 0.35 * cust["_price_sensitivity"])
        if self.rng.random() > use_p:
            return None, 0.0

        if is_first:
            chosen = max(candidates, key=lambda c: self._discount_value(c, subtotal))
        else:
            chosen = candidates[int(self.rng.integers(0, len(candidates)))]
        return chosen["id"], self._discount_value(chosen, subtotal)

    @staticmethod
    def _discount_value(c: dict, subtotal: float) -> float:
        if c["discount_type"] == "flat":
            disc = c["discount_value"]
        else:
            disc = subtotal * c["discount_value"] / 100.0
        disc = min(disc, c["max_discount"], subtotal)
        return round(float(disc), 2)
