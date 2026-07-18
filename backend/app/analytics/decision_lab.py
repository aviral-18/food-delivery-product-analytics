"""
Product Decision Lab — a scenario simulator.

Given a filtered baseline, estimate the directional impact of product/pricing
levers on orders, GMV, net revenue, contribution margin, repeat rate and CLV.
The model is an explainable elasticity layer calibrated with documented
assumptions (see docs/BUSINESS_ASSUMPTIONS.md). Every output is clearly labelled
as an ESTIMATE derived from historical relationships — not a promise.

Supported levers (magnitude semantics in parentheses):
  * reduce_coupon_value       (% reduction in coupon discount, 0-100)
  * increase_delivery_fee     (INR added per order)
  * improve_delivery_time     (minutes faster, average)
  * add_restaurants           (% increase in active supply)
  * increase_marketing_spend  (% increase in acquisition budget)
  * change_free_delivery_threshold (INR change to the free-delivery threshold)
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.analytics import executive
from app.analytics.filters import Filters
from app.analytics.query import run_query


# ---- Documented elasticities (dimensionless unless noted) ----------------- #
class Elasticity:
    COUPON_PRICE = 0.45          # order sensitivity to lost coupon value
    COUPON_RETENTION = 0.30      # first->repeat sensitivity to first-order incentive
    DELIVERY_FEE = 0.60          # order sensitivity to effective price increase
    DELIVERY_TIME_REPEAT = 0.012 # repeat-rate lift per minute faster (capped)
    SUPPLY = 0.25                # order lift per unit supply increase (diminishing)
    MARKETING = 0.55             # new-customer lift per unit spend increase
    THRESHOLD_FEE = 0.006        # share of orders crossing free-delivery per INR


@dataclass
class LeverResult:
    lever: str
    magnitude: float
    assumptions: list[str]
    order_change_pct: float
    per_order_margin_change: float  # INR
    retention_change_pct: float


def _baseline(db: Session, filters: Filters) -> dict:
    agg = executive._aggregate(db, filters)
    extra = run_query(db, """
        SELECT
            AVG(o.discount_amount) AS avg_discount,
            AVG(o.delivery_fee)    AS avg_delivery_fee,
            AVG(o.subtotal)        AS avg_subtotal,
            AVG(o.contribution_margin) AS avg_margin
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE o.status='delivered'{filters}
    """.format(filters=filters.render()[0]), filters.render()[1], filters.render()[2]).first() or {}
    return {
        "delivered_orders": agg["delivered_orders"],
        "gmv": agg["gmv"],
        "net_revenue": agg["net_revenue"],
        "contribution_margin": agg["contribution_margin"],
        "aov": agg["aov"],
        "repeat_rate": agg["repeat_purchase_rate"],
        "coupon_redemption_rate": agg["coupon_redemption_rate"],
        "avg_discount": float(extra.get("avg_discount") or 0),
        "avg_delivery_fee": float(extra.get("avg_delivery_fee") or 0),
        "avg_subtotal": float(extra.get("avg_subtotal") or 0),
        "avg_margin": float(extra.get("avg_margin") or 0),
    }


# --------------------------------------------------------------------------- #
#  Individual levers
# --------------------------------------------------------------------------- #
def _lever_reduce_coupon(b: dict, pct: float) -> LeverResult:
    frac = pct / 100.0
    # Marginal orders lost = coupon share * reduction * elasticity.
    order_change = -b["coupon_redemption_rate"] * frac * Elasticity.COUPON_PRICE
    # Platform funds ~60% of discount; saving lifts per-order margin.
    saved = b["avg_discount"] * b["coupon_redemption_rate"] * frac * 0.6
    retention_change = -b["coupon_redemption_rate"] * frac * Elasticity.COUPON_RETENTION * 0.5
    return LeverResult(
        "reduce_coupon_value", pct,
        [f"Coupon redemption baseline {b['coupon_redemption_rate']*100:.1f}%",
         f"Price elasticity {Elasticity.COUPON_PRICE}",
         "Platform funds 60% of discount"],
        order_change * 100, saved, retention_change * 100,
    )


def _lever_delivery_fee(b: dict, inr: float) -> LeverResult:
    order_change = -(inr / max(b["aov"], 1)) * Elasticity.DELIVERY_FEE
    return LeverResult(
        "increase_delivery_fee", inr,
        [f"AOV baseline Rs {b['aov']:.0f}", f"Fee elasticity {Elasticity.DELIVERY_FEE}"],
        order_change * 100, inr * 0.95, 0.0,  # most of the fee flows to margin
    )


def _lever_improve_time(b: dict, minutes: float) -> LeverResult:
    retention_change = min(0.06, minutes * Elasticity.DELIVERY_TIME_REPEAT)
    # Faster delivery -> fewer refunds/complaints -> small margin lift, small fleet cost.
    per_order_margin = minutes * 0.4 - minutes * 0.8  # net slight cost of speed
    order_change = retention_change * 0.5
    return LeverResult(
        "improve_delivery_time", minutes,
        [f"Repeat lift {Elasticity.DELIVERY_TIME_REPEAT}/min (capped 6%)",
         "Speed adds fleet cost partially offset by fewer refunds"],
        order_change * 100, per_order_margin, retention_change * 100,
    )


def _lever_add_restaurants(b: dict, pct: float) -> LeverResult:
    frac = pct / 100.0
    order_change = frac * Elasticity.SUPPLY / (1 + frac)  # diminishing returns
    return LeverResult(
        "add_restaurants", pct,
        [f"Supply elasticity {Elasticity.SUPPLY} with diminishing returns"],
        order_change * 100, 0.0, 0.0,
    )


def _lever_marketing(b: dict, pct: float) -> LeverResult:
    frac = pct / 100.0
    order_change = frac * Elasticity.MARKETING * 0.4  # new customers are a share of volume
    return LeverResult(
        "increase_marketing_spend", pct,
        [f"Marketing elasticity {Elasticity.MARKETING}", "New customers ~40% of incremental volume"],
        order_change * 100, -b["avg_margin"] * 0.15, 0.0,  # CAC dilutes near-term margin
    )


def _lever_threshold(b: dict, inr: float) -> LeverResult:
    # Raising threshold => more orders pay delivery fee (margin up, small volume dip).
    orders_now_paying = inr * Elasticity.THRESHOLD_FEE
    order_change = -orders_now_paying * 0.2
    per_order_margin = orders_now_paying * b["avg_delivery_fee"] * 0.5
    return LeverResult(
        "change_free_delivery_threshold", inr,
        [f"~{Elasticity.THRESHOLD_FEE*100:.1f}% of orders cross the threshold per INR"],
        order_change * 100, per_order_margin, 0.0,
    )


_LEVERS = {
    "reduce_coupon_value": _lever_reduce_coupon,
    "increase_delivery_fee": _lever_delivery_fee,
    "improve_delivery_time": _lever_improve_time,
    "add_restaurants": _lever_add_restaurants,
    "increase_marketing_spend": _lever_marketing,
    "change_free_delivery_threshold": _lever_threshold,
}


def available_levers() -> list[str]:
    return list(_LEVERS.keys())


# --------------------------------------------------------------------------- #
#  Simulation
# --------------------------------------------------------------------------- #
def simulate(db: Session, filters: Filters, levers: list[dict]) -> dict:
    """
    `levers` is a list of {"lever": name, "magnitude": float}. Effects combine
    multiplicatively on order volume and additively on per-order margin.
    """
    b = _baseline(db, filters)
    applied: list[LeverResult] = []
    for spec in levers:
        name = spec.get("lever")
        mag = float(spec.get("magnitude", 0))
        fn = _LEVERS.get(name)
        if fn:
            applied.append(fn(b, mag))

    order_mult = 1.0
    per_order_margin_delta = 0.0
    retention_delta_pct = 0.0
    for r in applied:
        order_mult *= (1 + r.order_change_pct / 100.0)
        per_order_margin_delta += r.per_order_margin_change
        retention_delta_pct += r.retention_change_pct

    new_orders = b["delivered_orders"] * order_mult
    new_aov = b["aov"]  # AOV held ~constant; economics move via per-order margin
    new_gmv = new_orders * new_aov
    new_margin_per_order = b["avg_margin"] + per_order_margin_delta
    new_contribution = new_orders * new_margin_per_order
    # Net revenue moves with volume + coupon savings captured in margin delta.
    net_rev_per_order = (b["net_revenue"] / b["delivered_orders"]) if b["delivered_orders"] else 0
    new_net_revenue = new_orders * (net_rev_per_order + per_order_margin_delta * 0.7)
    new_repeat = max(0.0, min(0.95, b["repeat_rate"] + retention_delta_pct / 100.0))

    def delta(new, old):
        return {
            "baseline": round(old, 2),
            "simulated": round(new, 2),
            "delta": round(new - old, 2),
            "delta_pct": round((new - old) / old * 100, 1) if old else None,
        }

    return {
        "disclaimer": "Simulation estimate based on historical elasticities. Directional guidance only, not a forecast.",
        "levers_applied": [
            {"lever": r.lever, "magnitude": r.magnitude, "assumptions": r.assumptions,
             "order_change_pct": round(r.order_change_pct, 2),
             "per_order_margin_change": round(r.per_order_margin_change, 2),
             "retention_change_pct": round(r.retention_change_pct, 2)}
            for r in applied
        ],
        "results": {
            "delivered_orders": delta(new_orders, b["delivered_orders"]),
            "gmv": delta(new_gmv, b["gmv"]),
            "net_revenue": delta(new_net_revenue, b["net_revenue"]),
            "contribution_margin": delta(new_contribution, b["contribution_margin"]),
            "repeat_purchase_rate": delta(new_repeat, b["repeat_rate"]),
        },
        "baseline": {k: round(v, 4) if isinstance(v, float) else v for k, v in b.items()},
    }
