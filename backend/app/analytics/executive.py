"""
Executive dashboard metrics: headline KPIs (with period-over-period deltas),
revenue trends, growth, and the weighted Product Health Index.
"""
from __future__ import annotations

import dataclasses
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.analytics.filters import Filters
from app.analytics.query import run_query


# --------------------------------------------------------------------------- #
#  Core aggregate
# --------------------------------------------------------------------------- #
_AGGREGATE_SQL = """
SELECT
    COUNT(*)                                                                AS total_orders,
    SUM(CASE WHEN o.status = 'delivered' THEN 1 ELSE 0 END)                 AS delivered_orders,
    SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END)                 AS cancelled_orders,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.subtotal END), 0)  AS gmv,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.gross_revenue END), 0)       AS gross_revenue,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.net_revenue END), 0)         AS net_revenue,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.contribution_margin END), 0) AS contribution_margin,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.discount_amount END), 0)     AS discount_given,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.refund_amount END), 0)       AS refund_value,
    SUM(CASE WHEN o.status = 'delivered' AND o.is_late THEN 1 ELSE 0 END)     AS late_orders,
    SUM(CASE WHEN o.status = 'delivered' AND o.is_refunded THEN 1 ELSE 0 END) AS refunded_orders,
    SUM(CASE WHEN o.status = 'delivered' AND o.coupon_id IS NOT NULL THEN 1 ELSE 0 END) AS coupon_orders,
    AVG(CASE WHEN o.status = 'delivered' THEN o.delivery_minutes END)      AS avg_delivery_minutes,
    AVG(CASE WHEN o.status = 'delivered' THEN o.restaurant_rating END)     AS avg_restaurant_rating,
    AVG(CASE WHEN o.status = 'delivered' THEN o.delivery_rating END)       AS avg_delivery_rating,
    COUNT(DISTINCT o.customer_id)                                          AS active_customers,
    SUM(CASE WHEN o.is_first_order THEN 1 ELSE 0 END)                      AS new_customers
FROM orders o
JOIN restaurants r ON r.id = o.restaurant_id
JOIN customers   c ON c.id = o.customer_id
WHERE 1 = 1{filters}
"""

_REPEAT_SQL = """
SELECT
    COUNT(*)                                        AS active_customers,
    SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END)         AS repeat_customers
FROM (
    SELECT o.customer_id, COUNT(*) AS n
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE o.status = 'delivered'{filters}
    GROUP BY o.customer_id
) t
"""


def _aggregate(db: Session, filters: Filters) -> dict:
    clause, params, expanding = filters.render()
    agg = run_query(db, _AGGREGATE_SQL.format(filters=clause), params, expanding).first() or {}
    rep = run_query(db, _REPEAT_SQL.format(filters=clause), params, expanding).first() or {}
    agg = {k: (v if v is not None else 0) for k, v in agg.items()}

    delivered = agg["delivered_orders"] or 0
    total = agg["total_orders"] or 0
    gmv = float(agg["gmv"])
    out = {
        **agg,
        "gmv": gmv,
        "net_revenue": float(agg["net_revenue"]),
        "gross_revenue": float(agg["gross_revenue"]),
        "contribution_margin": float(agg["contribution_margin"]),
        "discount_given": float(agg["discount_given"]),
        "aov": round(gmv / delivered, 2) if delivered else 0.0,
        "cancellation_rate": round((agg["cancelled_orders"] or 0) / total, 4) if total else 0.0,
        "late_delivery_rate": round((agg["late_orders"] or 0) / delivered, 4) if delivered else 0.0,
        "refund_rate": round((agg["refunded_orders"] or 0) / delivered, 4) if delivered else 0.0,
        "coupon_redemption_rate": round((agg["coupon_orders"] or 0) / delivered, 4) if delivered else 0.0,
        "delivery_success_rate": round(delivered / total, 4) if total else 0.0,
        "contribution_margin_pct": round(float(agg["contribution_margin"]) / gmv, 4) if gmv else 0.0,
        "take_rate": round(float(agg["net_revenue"]) / gmv, 4) if gmv else 0.0,
        "avg_delivery_minutes": round(float(agg["avg_delivery_minutes"] or 0), 1),
        "avg_restaurant_rating": round(float(agg["avg_restaurant_rating"] or 0), 2),
        "avg_delivery_rating": round(float(agg["avg_delivery_rating"] or 0), 2),
        "repeat_customers": rep.get("repeat_customers") or 0,
        "repeat_purchase_rate": round((rep.get("repeat_customers") or 0) / (rep.get("active_customers") or 1), 4),
    }
    return out


def _pct_change(cur: float, prev: float) -> float | None:
    if prev in (0, None):
        return None
    return round((cur - prev) / prev * 100.0, 1)


def kpi_summary(db: Session, filters: Filters) -> dict:
    """Headline KPI cards with previous-equal-length-period deltas."""
    cur = _aggregate(db, filters)

    # Previous comparison window (same length, immediately preceding).
    s = date.fromisoformat(filters.effective_start)
    e = date.fromisoformat(filters.effective_end)
    length = (e - s).days + 1
    prev_e = s - timedelta(days=1)
    prev_s = prev_e - timedelta(days=length - 1)
    prev_filters = dataclasses.replace(filters, start_date=prev_s.isoformat(), end_date=prev_e.isoformat())
    prev = _aggregate(db, prev_filters)

    def card(key: str, value, fmt: str, invert: bool = False):
        prev_val = prev.get(key)
        delta = _pct_change(float(value or 0), float(prev_val or 0)) if isinstance(value, (int, float)) else None
        return {
            "key": key, "value": value, "format": fmt,
            "delta_pct": delta,
            "trend": None if delta is None else ("up" if delta >= 0 else "down"),
            "is_positive": None if delta is None else ((delta >= 0) != invert),
        }

    cards = [
        card("net_revenue", round(cur["net_revenue"], 2), "currency"),
        card("gmv", round(cur["gmv"], 2), "currency"),
        card("delivered_orders", cur["delivered_orders"], "number"),
        card("aov", cur["aov"], "currency"),
        card("active_customers", cur["active_customers"], "number"),
        card("new_customers", cur["new_customers"], "number"),
        card("repeat_purchase_rate", cur["repeat_purchase_rate"], "percent"),
        card("contribution_margin", round(cur["contribution_margin"], 2), "currency"),
        card("contribution_margin_pct", cur["contribution_margin_pct"], "percent"),
        card("avg_delivery_minutes", cur["avg_delivery_minutes"], "minutes", invert=True),
        card("late_delivery_rate", cur["late_delivery_rate"], "percent", invert=True),
        card("cancellation_rate", cur["cancellation_rate"], "percent", invert=True),
        card("refund_rate", cur["refund_rate"], "percent", invert=True),
        card("coupon_redemption_rate", cur["coupon_redemption_rate"], "percent"),
    ]
    return {
        "period": {"start": filters.effective_start, "end": filters.effective_end},
        "comparison_period": {"start": prev_s.isoformat(), "end": prev_e.isoformat()},
        "cards": cards,
        "raw": cur,
    }


# --------------------------------------------------------------------------- #
#  Revenue trend
# --------------------------------------------------------------------------- #
_TREND_SQL = """
SELECT
    DATE_TRUNC('{grain}', o.order_date) AS period,
    COUNT(*)                                                          AS orders,
    SUM(CASE WHEN o.status = 'delivered' THEN 1 ELSE 0 END)           AS delivered_orders,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.subtotal END), 0)     AS gmv,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.net_revenue END), 0)  AS net_revenue,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.contribution_margin END), 0) AS contribution_margin,
    COUNT(DISTINCT o.customer_id)                                     AS active_customers
FROM orders o
JOIN restaurants r ON r.id = o.restaurant_id
JOIN customers   c ON c.id = o.customer_id
WHERE 1 = 1{filters}
GROUP BY DATE_TRUNC('{grain}', o.order_date)
ORDER BY period
"""

_GRAINS = {"day", "week", "month", "quarter", "year"}


def revenue_trend(db: Session, filters: Filters, grain: str = "month") -> dict:
    grain = grain if grain in _GRAINS else "month"
    clause, params, expanding = filters.render()
    qr = run_query(db, _TREND_SQL.format(grain=grain, filters=clause), params, expanding)
    series = []
    for row in qr.rows:
        period = row["period"]
        series.append({
            "period": str(period)[:10],
            "orders": row["orders"],
            "delivered_orders": row["delivered_orders"],
            "gmv": round(float(row["gmv"]), 2),
            "net_revenue": round(float(row["net_revenue"]), 2),
            "contribution_margin": round(float(row["contribution_margin"]), 2),
            "active_customers": row["active_customers"],
        })
    # Attach MoM growth on net_revenue.
    for i in range(1, len(series)):
        prev = series[i - 1]["net_revenue"]
        series[i]["net_revenue_growth_pct"] = _pct_change(series[i]["net_revenue"], prev)
    return {"grain": grain, "series": series, "sql": qr.sql, "execution_ms": qr.execution_ms}


# --------------------------------------------------------------------------- #
#  Growth (new vs returning, restaurant supply)
# --------------------------------------------------------------------------- #
_GROWTH_SQL = """
SELECT
    DATE_TRUNC('month', o.order_date) AS period,
    COUNT(DISTINCT o.customer_id)                                          AS active_customers,
    COUNT(DISTINCT CASE WHEN o.is_first_order THEN o.customer_id END)      AS new_customers,
    COUNT(DISTINCT o.restaurant_id)                                        AS active_restaurants,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.net_revenue END), 0) AS net_revenue
FROM orders o
JOIN restaurants r ON r.id = o.restaurant_id
JOIN customers   c ON c.id = o.customer_id
WHERE 1 = 1{filters}
GROUP BY DATE_TRUNC('month', o.order_date)
ORDER BY period
"""


def growth(db: Session, filters: Filters) -> dict:
    clause, params, expanding = filters.render()
    qr = run_query(db, _GROWTH_SQL.format(filters=clause), params, expanding)
    series = []
    for row in qr.rows:
        active = row["active_customers"] or 0
        new = row["new_customers"] or 0
        series.append({
            "period": str(row["period"])[:10],
            "active_customers": active,
            "new_customers": new,
            "returning_customers": active - new,
            "active_restaurants": row["active_restaurants"],
            "net_revenue": round(float(row["net_revenue"]), 2),
        })
    for i in range(1, len(series)):
        for k in ("active_customers", "new_customers", "net_revenue"):
            series[i][f"{k}_growth_pct"] = _pct_change(series[i][k], series[i - 1][k])
    return {"series": series, "sql": qr.sql, "execution_ms": qr.execution_ms}


# --------------------------------------------------------------------------- #
#  Product Health Index (weighted composite score)
# --------------------------------------------------------------------------- #
# Each sub-score is normalised to 0-100 against a documented target band, then
# combined with business-priority weights. Methodology lives in docs.
HEALTH_WEIGHTS = {
    "growth": 0.22,        # net revenue MoM growth
    "retention": 0.22,     # repeat purchase rate
    "unit_economics": 0.20,  # contribution margin %
    "experience": 0.18,    # ratings + (1 - refund)
    "operations": 0.18,    # on-time delivery + (1 - cancellation)
}


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def health_index(db: Session, filters: Filters) -> dict:
    cur = _aggregate(db, filters)
    trend = revenue_trend(db, filters, "month")["series"]

    # Growth: average of last up-to-3 MoM growth %, mapped 0%->50, +15%->100.
    growths = [s.get("net_revenue_growth_pct") for s in trend if s.get("net_revenue_growth_pct") is not None]
    recent = growths[-3:] if growths else []
    avg_growth = sum(recent) / len(recent) if recent else 0.0
    growth_score = _clamp(50 + (avg_growth / 15.0) * 50)

    # Retention: repeat rate 0%->0, 70%->100 (band).
    retention_score = _clamp(cur["repeat_purchase_rate"] / 0.70 * 100)

    # Unit economics: CM% -2%->0, 12%->100.
    ue = cur["contribution_margin_pct"]
    ue_score = _clamp((ue + 0.02) / 0.14 * 100)

    # Experience: rating 3.0->0, 5.0->100, penalised by refund rate.
    rating_score = _clamp((cur["avg_restaurant_rating"] - 3.0) / 2.0 * 100)
    experience_score = _clamp(rating_score * (1 - cur["refund_rate"] * 3))

    # Operations: on-time share + low cancellation.
    ontime = 1 - cur["late_delivery_rate"]
    ops_score = _clamp((ontime * 0.6 + (1 - cur["cancellation_rate"]) * 0.4) * 100)

    subscores = {
        "growth": round(growth_score, 1),
        "retention": round(retention_score, 1),
        "unit_economics": round(ue_score, 1),
        "experience": round(experience_score, 1),
        "operations": round(ops_score, 1),
    }
    overall = round(sum(subscores[k] * w for k, w in HEALTH_WEIGHTS.items()), 1)
    grade = (
        "A" if overall >= 80 else "B" if overall >= 65 else
        "C" if overall >= 50 else "D" if overall >= 35 else "F"
    )
    return {
        "overall_score": overall,
        "grade": grade,
        "subscores": subscores,
        "weights": HEALTH_WEIGHTS,
        "drivers": {
            "net_revenue_mom_growth_pct": round(avg_growth, 1),
            "repeat_purchase_rate": cur["repeat_purchase_rate"],
            "contribution_margin_pct": cur["contribution_margin_pct"],
            "avg_restaurant_rating": cur["avg_restaurant_rating"],
            "on_time_rate": round(ontime, 4),
            "cancellation_rate": cur["cancellation_rate"],
        },
    }
