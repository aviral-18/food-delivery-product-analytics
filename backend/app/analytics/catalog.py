"""
Catalog & geography analytics: restaurant performance and ranking, cuisine
performance, and city performance (with marketing efficiency).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.analytics.filters import Filters
from app.analytics.query import run_query


# --------------------------------------------------------------------------- #
#  Restaurant performance & ranking
# --------------------------------------------------------------------------- #
def restaurant_performance(db: Session, filters: Filters, limit: int = 50, order_by: str = "net_revenue") -> dict:
    clause, params, expanding = filters.render()
    allowed = {"net_revenue", "orders", "gmv", "contribution_margin", "avg_rating", "late_rate"}
    order_by = order_by if order_by in allowed else "net_revenue"

    sql = """
    SELECT
        o.restaurant_id,
        rest.name           AS restaurant_name,
        rest.city_id        AS city_id,
        rest.cuisine_id     AS cuisine_id,
        rest.price_tier     AS price_tier,
        COUNT(*)                                                        AS orders,
        SUM(CASE WHEN o.status='delivered' THEN 1 ELSE 0 END)          AS delivered_orders,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.subtotal END),0)     AS gmv,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.net_revenue END),0)  AS net_revenue,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.contribution_margin END),0) AS contribution_margin,
        AVG(CASE WHEN o.status='delivered' THEN o.restaurant_rating END)        AS avg_rating,
        SUM(CASE WHEN o.status='delivered' AND o.is_late THEN 1 ELSE 0 END)*1.0
            / NULLIF(SUM(CASE WHEN o.status='delivered' THEN 1 ELSE 0 END),0)   AS late_rate,
        SUM(CASE WHEN o.status='cancelled' THEN 1 ELSE 0 END)*1.0/COUNT(*)      AS cancel_rate,
        COUNT(DISTINCT o.customer_id)                                          AS unique_customers,
        SUM(CASE WHEN o.status='delivered' AND o.is_refunded THEN 1 ELSE 0 END) AS refunded_orders
    FROM orders o
    JOIN restaurants rest ON rest.id = o.restaurant_id
    JOIN restaurants r    ON r.id = o.restaurant_id
    JOIN customers   c    ON c.id = o.customer_id
    WHERE 1=1{filters}
    GROUP BY o.restaurant_id, rest.name, rest.city_id, rest.cuisine_id, rest.price_tier
    ORDER BY {order_by} DESC
    LIMIT :lim
    """.format(filters=clause, order_by=order_by)
    p = {**params, "lim": limit}
    qr = run_query(db, sql, p, expanding)

    rows = []
    for r in qr.rows:
        delivered = r["delivered_orders"] or 0
        rows.append({
            "restaurant_id": r["restaurant_id"],
            "restaurant_name": r["restaurant_name"],
            "city_id": r["city_id"],
            "cuisine_id": r["cuisine_id"],
            "price_tier": r["price_tier"],
            "orders": r["orders"],
            "delivered_orders": delivered,
            "gmv": round(float(r["gmv"]), 2),
            "net_revenue": round(float(r["net_revenue"]), 2),
            "contribution_margin": round(float(r["contribution_margin"]), 2),
            "avg_rating": round(float(r["avg_rating"] or 0), 2),
            "late_rate": round(float(r["late_rate"] or 0), 4),
            "cancel_rate": round(float(r["cancel_rate"] or 0), 4),
            "unique_customers": r["unique_customers"],
            "refunded_orders": r["refunded_orders"] or 0,
        })
    return {"restaurants": rows, "order_by": order_by, "sql": qr.sql, "execution_ms": qr.execution_ms}


def restaurant_ranking(db: Session, filters: Filters, limit: int = 20) -> dict:
    """Composite quality-vs-volume ranking (top and bottom performers)."""
    perf = restaurant_performance(db, filters, limit=1000, order_by="net_revenue")["restaurants"]
    if not perf:
        return {"top": [], "bottom": [], "sql": ""}
    max_rev = max(r["net_revenue"] for r in perf) or 1
    for r in perf:
        # Composite: revenue scale (log-ish via share) + rating - penalties.
        rev_score = (r["net_revenue"] / max_rev) * 40
        rating_score = (r["avg_rating"] / 5.0) * 30
        reliability = (1 - r["late_rate"]) * 20 + (1 - r["cancel_rate"]) * 10
        r["performance_score"] = round(rev_score + rating_score + reliability, 1)
    ranked = sorted(perf, key=lambda x: x["performance_score"], reverse=True)
    # "bottom" = poor experience among restaurants with meaningful volume.
    volume = [r for r in perf if r["delivered_orders"] >= 10]
    worst = sorted(volume, key=lambda x: (x["avg_rating"], -x["late_rate"]))[:limit]
    return {"top": ranked[:limit], "bottom": worst, "total_ranked": len(perf)}


# --------------------------------------------------------------------------- #
#  Cuisine performance
# --------------------------------------------------------------------------- #
def cuisine_performance(db: Session, filters: Filters) -> dict:
    clause, params, expanding = filters.render()
    sql = """
    SELECT
        r.cuisine_id,
        COUNT(*)                                                          AS orders,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.subtotal END),0)     AS gmv,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.net_revenue END),0)  AS net_revenue,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.contribution_margin END),0) AS contribution_margin,
        COALESCE(AVG(CASE WHEN o.status='delivered' THEN o.subtotal END),0)     AS aov,
        AVG(CASE WHEN o.status='delivered' THEN o.restaurant_rating END)        AS avg_rating,
        COUNT(DISTINCT o.customer_id)                                          AS unique_customers,
        COUNT(DISTINCT o.restaurant_id)                                        AS restaurants
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE 1=1{filters}
    GROUP BY r.cuisine_id
    ORDER BY net_revenue DESC
    """.format(filters=clause)
    qr = run_query(db, sql, params, expanding)
    rows = [{
        "cuisine_id": r["cuisine_id"],
        "orders": r["orders"],
        "gmv": round(float(r["gmv"]), 2),
        "net_revenue": round(float(r["net_revenue"]), 2),
        "contribution_margin": round(float(r["contribution_margin"]), 2),
        "aov": round(float(r["aov"]), 2),
        "avg_rating": round(float(r["avg_rating"] or 0), 2),
        "unique_customers": r["unique_customers"],
        "restaurants": r["restaurants"],
    } for r in qr.rows]
    return {"cuisines": rows, "sql": qr.sql, "execution_ms": qr.execution_ms}


# --------------------------------------------------------------------------- #
#  City performance (+ marketing efficiency)
# --------------------------------------------------------------------------- #
def city_performance(db: Session, filters: Filters) -> dict:
    clause, params, expanding = filters.render()
    perf_sql = """
    SELECT
        o.city_id,
        COUNT(*)                                                          AS orders,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.subtotal END),0)     AS gmv,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.net_revenue END),0)  AS net_revenue,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.contribution_margin END),0) AS contribution_margin,
        COALESCE(AVG(CASE WHEN o.status='delivered' THEN o.subtotal END),0)     AS aov,
        COUNT(DISTINCT o.customer_id)                                          AS active_customers,
        COUNT(DISTINCT CASE WHEN o.is_first_order THEN o.customer_id END)      AS new_customers,
        COUNT(DISTINCT o.restaurant_id)                                        AS active_restaurants,
        SUM(CASE WHEN o.status='delivered' AND o.is_late THEN 1 ELSE 0 END)*1.0
            / NULLIF(SUM(CASE WHEN o.status='delivered' THEN 1 ELSE 0 END),0)  AS late_rate
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE 1=1{filters}
    GROUP BY o.city_id
    ORDER BY net_revenue DESC
    """.format(filters=clause)
    perf = {row["city_id"]: row for row in run_query(db, perf_sql, params, expanding).rows}

    # Marketing spend by city within the window (independent of order filters).
    spend_sql = """
    SELECT city_id, COALESCE(SUM(spend),0) AS spend, COALESCE(SUM(installs),0) AS installs
    FROM marketing_spend
    WHERE month >= :f_start AND month <= :f_end
    GROUP BY city_id
    """
    spend = {row["city_id"]: row for row in run_query(db, spend_sql, {
        "f_start": filters.effective_start, "f_end": filters.effective_end,
    }).rows}

    cities = []
    for city_id, row in perf.items():
        sp = spend.get(city_id, {})
        spend_val = float(sp.get("spend") or 0)
        new_cust = row["new_customers"] or 0
        net_rev = float(row["net_revenue"])
        cities.append({
            "city_id": city_id,
            "orders": row["orders"],
            "gmv": round(float(row["gmv"]), 2),
            "net_revenue": round(net_rev, 2),
            "contribution_margin": round(float(row["contribution_margin"]), 2),
            "aov": round(float(row["aov"]), 2),
            "active_customers": row["active_customers"],
            "new_customers": new_cust,
            "active_restaurants": row["active_restaurants"],
            "late_rate": round(float(row["late_rate"] or 0), 4),
            "marketing_spend": round(spend_val, 2),
            "cac": round(spend_val / new_cust, 2) if new_cust else None,
            "roas": round(net_rev / spend_val, 2) if spend_val else None,
        })
    cities.sort(key=lambda x: x["net_revenue"], reverse=True)
    return {"cities": cities, "sql": perf_sql.strip(), "spend_sql": spend_sql.strip()}
