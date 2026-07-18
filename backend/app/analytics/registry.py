"""
SQL Explorer registry.

A curated catalogue of the canonical SQL behind the platform's key metrics, each
tagged with the business question it answers and a plain-English explanation.
Powers the internal SQL Explorer page (view the query, run it against the live
DB, preview results, see execution time) and doubles as living SQL documentation.

Also exposes a guarded read-only executor for ad-hoc analyst queries: single
SELECT only, no DML/DDL, auto-LIMIT.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.analytics.filters import Filters
from app.analytics.query import run_query


@dataclass
class ExplorableQuery:
    key: str
    category: str
    title: str
    business_question: str
    explanation: str
    sql: str  # canonical PostgreSQL with an optional {filters} placeholder


CATALOG: list[ExplorableQuery] = [
    ExplorableQuery(
        "gmv_net_revenue", "Revenue",
        "GMV & Net Revenue by month",
        "How are top-line GMV and platform net revenue trending?",
        "GMV is the food value of delivered orders; net revenue is platform take "
        "(commission + fees) minus platform-funded discounts and refunds.",
        """
SELECT DATE_TRUNC('month', o.order_date)                              AS month,
       COUNT(*) FILTER_EQUIV                                          AS delivered_orders,
       SUM(o.subtotal)                                                AS gmv,
       SUM(o.net_revenue)                                             AS net_revenue,
       ROUND(SUM(o.net_revenue) / NULLIF(SUM(o.subtotal),0) * 100, 2) AS take_rate_pct
FROM orders o
WHERE o.status = 'delivered'{filters}
GROUP BY DATE_TRUNC('month', o.order_date)
ORDER BY month
""".replace("COUNT(*) FILTER_EQUIV", "COUNT(*)"),
    ),
    ExplorableQuery(
        "aov", "Revenue",
        "Average Order Value (AOV)",
        "What is the average basket size of a delivered order?",
        "AOV = total food value (GMV) divided by number of delivered orders.",
        """
SELECT ROUND(AVG(o.subtotal), 2) AS aov,
       COUNT(*)                  AS delivered_orders
FROM orders o
WHERE o.status = 'delivered'{filters}
""",
    ),
    ExplorableQuery(
        "repeat_rate", "Retention",
        "Repeat Purchase Rate",
        "What share of activated customers order more than once?",
        "Customers with >= 2 delivered orders divided by all customers who ordered.",
        """
SELECT ROUND(AVG(CASE WHEN n >= 2 THEN 1.0 ELSE 0.0 END), 4) AS repeat_purchase_rate,
       COUNT(*)                                              AS activated_customers
FROM (
    SELECT o.customer_id, COUNT(*) AS n
    FROM orders o
    WHERE o.status = 'delivered'{filters}
    GROUP BY o.customer_id
) t
""",
    ),
    ExplorableQuery(
        "cohort_base", "Retention",
        "Cohort activity (customer x order-month)",
        "Which months did each customer place orders (for cohort retention)?",
        "Base grain for the retention matrix: one row per customer per active "
        "order-month. The matrix pivots first-order-month vs months-since.",
        """
SELECT o.customer_id,
       DATE_TRUNC('month', o.order_date) AS order_month
FROM orders o
WHERE o.status = 'delivered'{filters}
GROUP BY o.customer_id, DATE_TRUNC('month', o.order_date)
ORDER BY o.customer_id, order_month
""",
    ),
    ExplorableQuery(
        "rfm", "Segmentation",
        "RFM base (recency / frequency / monetary)",
        "What are each customer's recency, frequency and spend?",
        "Per-customer building blocks scored into quintiles to assign RFM segments "
        "(Champions, Loyal, At Risk, Hibernating, ...).",
        """
SELECT o.customer_id,
       MAX(o.order_date)  AS last_order_date,
       COUNT(*)           AS frequency,
       SUM(o.subtotal)    AS monetary,
       SUM(o.net_revenue) AS net_revenue
FROM orders o
WHERE o.status = 'delivered'{filters}
GROUP BY o.customer_id
""",
    ),
    ExplorableQuery(
        "clv", "Retention",
        "Customer Lifetime Value (historical)",
        "How much net revenue and margin has each customer generated?",
        "Historical CLV per customer, with order count and lifespan for predictive "
        "extrapolation.",
        """
SELECT o.customer_id,
       COUNT(*)                    AS orders,
       SUM(o.net_revenue)          AS clv_net_revenue,
       SUM(o.contribution_margin)  AS clv_margin,
       MIN(o.order_date)           AS first_order,
       MAX(o.order_date)           AS last_order
FROM orders o
WHERE o.status = 'delivered'{filters}
GROUP BY o.customer_id
ORDER BY clv_net_revenue DESC
""",
    ),
    ExplorableQuery(
        "delay_root_cause", "Operations",
        "Delivery delay decomposition",
        "What drives delivery time — kitchen prep or last-mile?",
        "Splits average delivery time into prep vs travel/wait and computes the "
        "late-rate, revealing the dominant lever.",
        """
SELECT AVG(o.prep_minutes)                        AS avg_prep_minutes,
       AVG(o.delivery_minutes - o.prep_minutes)   AS avg_travel_wait_minutes,
       AVG(o.delivery_minutes)                    AS avg_total_minutes,
       AVG(CASE WHEN o.is_late THEN 1.0 ELSE 0.0 END) AS late_rate
FROM orders o
WHERE o.status = 'delivered'{filters}
""",
    ),
    ExplorableQuery(
        "late_by_weather", "Operations",
        "Late rate by weather",
        "How much does weather degrade the on-time promise?",
        "Late-delivery rate grouped by weather condition.",
        """
SELECT o.weather,
       COUNT(*)                                       AS delivered_orders,
       ROUND(AVG(CASE WHEN o.is_late THEN 1.0 ELSE 0.0 END), 4) AS late_rate,
       ROUND(AVG(o.delivery_minutes), 1)              AS avg_delivery_minutes
FROM orders o
WHERE o.status = 'delivered'{filters}
GROUP BY o.weather
ORDER BY late_rate DESC
""",
    ),
    ExplorableQuery(
        "cancellation_reasons", "Operations",
        "Cancellation reasons",
        "Why are orders being cancelled?",
        "Cancelled-order counts by reason.",
        """
SELECT o.cancellation_reason,
       COUNT(*) AS cancelled_orders
FROM orders o
WHERE o.status = 'cancelled'{filters}
GROUP BY o.cancellation_reason
ORDER BY cancelled_orders DESC
""",
    ),
    ExplorableQuery(
        "refund_vs_late", "Operations",
        "Refund rate: late vs on-time",
        "Do late deliveries cause more refunds?",
        "Compares refund rate for on-time vs late orders — quantifies the SLA-to-refund link.",
        """
SELECT o.is_late,
       COUNT(*)                                          AS delivered_orders,
       ROUND(AVG(CASE WHEN o.is_refunded THEN 1.0 ELSE 0.0 END), 4) AS refund_rate
FROM orders o
WHERE o.status = 'delivered'{filters}
GROUP BY o.is_late
""",
    ),
    ExplorableQuery(
        "peak_hours", "Demand",
        "Peak-hour demand heatmap",
        "When do orders peak across the week?",
        "Order counts by day-of-week and hour — the demand heatmap for staffing and surge.",
        """
SELECT EXTRACT(DOW  FROM o.order_datetime) AS day_of_week,
       EXTRACT(HOUR FROM o.order_datetime) AS hour_of_day,
       COUNT(*)                            AS orders
FROM orders o
WHERE 1 = 1{filters}
GROUP BY EXTRACT(DOW FROM o.order_datetime), EXTRACT(HOUR FROM o.order_datetime)
ORDER BY day_of_week, hour_of_day
""",
    ),
    ExplorableQuery(
        "coupon_effectiveness", "Marketing",
        "Coupon / campaign effectiveness",
        "Which campaigns drive profit, not just orders?",
        "Per-campaign redemptions, discount spent, and contribution margin returned "
        "per rupee of discount.",
        """
SELECT cp.campaign_name,
       COUNT(*)                                                     AS redemptions,
       SUM(o.discount_amount)                                       AS discount_given,
       SUM(o.contribution_margin)                                   AS contribution_margin,
       ROUND(SUM(o.contribution_margin) / NULLIF(SUM(o.discount_amount),0), 3) AS margin_per_discount_rupee
FROM orders o
JOIN coupons cp ON cp.id = o.coupon_id
WHERE o.status = 'delivered' AND o.coupon_id IS NOT NULL{filters}
GROUP BY cp.campaign_name
ORDER BY contribution_margin DESC
""",
    ),
    ExplorableQuery(
        "city_performance", "Geography",
        "City performance",
        "Which cities generate the most profitable volume?",
        "Per-city orders, net revenue, contribution margin and late rate.",
        """
SELECT o.city_id,
       COUNT(*)                                                    AS delivered_orders,
       SUM(o.subtotal)                                             AS gmv,
       SUM(o.net_revenue)                                          AS net_revenue,
       SUM(o.contribution_margin)                                 AS contribution_margin,
       ROUND(AVG(CASE WHEN o.is_late THEN 1.0 ELSE 0.0 END), 4)    AS late_rate
FROM orders o
WHERE o.status = 'delivered'{filters}
GROUP BY o.city_id
ORDER BY net_revenue DESC
""",
    ),
    ExplorableQuery(
        "restaurant_ranking", "Catalog",
        "Top restaurants by net revenue",
        "Which restaurants drive the business and how good is their experience?",
        "Per-restaurant orders, net revenue, rating and late rate.",
        """
SELECT o.restaurant_id,
       rest.name                                                   AS restaurant_name,
       COUNT(*)                                                    AS delivered_orders,
       SUM(o.net_revenue)                                          AS net_revenue,
       ROUND(AVG(o.restaurant_rating), 2)                          AS avg_rating,
       ROUND(AVG(CASE WHEN o.is_late THEN 1.0 ELSE 0.0 END), 4)    AS late_rate
FROM orders o
JOIN restaurants rest ON rest.id = o.restaurant_id
WHERE o.status = 'delivered'{filters}
GROUP BY o.restaurant_id, rest.name
ORDER BY net_revenue DESC
LIMIT 25
""",
    ),
    ExplorableQuery(
        "payment_mix", "Revenue",
        "Payment-method mix",
        "How do customers pay, and what is the gateway cost?",
        "Order share and gateway cost by payment method (COD has no gateway fee).",
        """
SELECT o.payment_method,
       COUNT(*)                        AS orders,
       SUM(o.total_amount)             AS gross_value,
       SUM(o.payment_gateway_cost)     AS gateway_cost
FROM orders o
WHERE o.status = 'delivered'{filters}
GROUP BY o.payment_method
ORDER BY orders DESC
""",
    ),
]

_BY_KEY = {q.key: q for q in CATALOG}


def list_queries() -> list[dict]:
    return [{
        "key": q.key, "category": q.category, "title": q.title,
        "business_question": q.business_question, "explanation": q.explanation,
        "sql": _clean(q.sql.replace("{filters}", "")),
    } for q in CATALOG]


def _clean(sql: str) -> str:
    return sql.strip()


def run_catalog_query(db: Session, key: str, filters: Filters, limit: int = 200) -> dict:
    q = _BY_KEY.get(key)
    if not q:
        raise KeyError(key)
    clause, params, expanding = filters.render(o="o", r="rest", c="c")
    # Only apply the date portion generically (these curated queries mostly join
    # just `orders`); city/date filters reference o.* which is always present.
    safe_clause, safe_params, safe_expanding = _orders_only_filter(filters)
    sql = q.sql.format(filters=safe_clause)
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip() + f"\nLIMIT {int(limit)}"
    qr = run_query(db, sql, safe_params, safe_expanding)
    return {
        "key": key, "title": q.title, "category": q.category,
        "business_question": q.business_question, "explanation": q.explanation,
        "sql": qr.sql, "execution_ms": qr.execution_ms,
        "columns": qr.columns, "rows": qr.rows[:limit], "row_count": len(qr.rows),
    }


def _orders_only_filter(filters: Filters) -> tuple[str, dict, list[str]]:
    """Subset of filters that only reference the orders table (safe for curated SQL)."""
    conds, params, expanding = [], {}, []
    if filters.start_date:
        conds.append("o.order_date >= :f_start"); params["f_start"] = filters.start_date
    if filters.end_date:
        conds.append("o.order_date <= :f_end"); params["f_end"] = filters.end_date
    if filters.city_ids:
        conds.append("o.city_id IN :f_city"); params["f_city"] = filters.city_ids; expanding.append("f_city")
    if filters.payment_methods:
        conds.append("o.payment_method IN :f_pay"); params["f_pay"] = filters.payment_methods; expanding.append("f_pay")
    if filters.day_parts:
        conds.append("o.day_part IN :f_daypart"); params["f_daypart"] = filters.day_parts; expanding.append("f_daypart")
    clause = (" AND " + " AND ".join(conds)) if conds else ""
    return clause, params, expanding


# --------------------------------------------------------------------------- #
#  Guarded ad-hoc executor
# --------------------------------------------------------------------------- #
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|ATTACH|"
    r"DETACH|PRAGMA|COPY|VACUUM|REINDEX|REPLACE|MERGE)\b",
    re.IGNORECASE,
)


def safe_execute(db: Session, sql: str, limit: int = 200) -> dict:
    """Execute a single read-only SELECT, blocking any mutation."""
    cleaned = sql.strip().rstrip(";")
    if ";" in cleaned:
        raise ValueError("Only a single statement is allowed.")
    if not re.match(r"^\s*(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise ValueError("Only SELECT / WITH queries are allowed.")
    if _FORBIDDEN.search(cleaned):
        raise ValueError("Query contains a forbidden keyword (read-only access).")
    if "LIMIT" not in cleaned.upper():
        cleaned += f"\nLIMIT {int(limit)}"
    qr = run_query(db, cleaned, {})
    return {
        "sql": qr.sql, "execution_ms": qr.execution_ms,
        "columns": qr.columns, "rows": qr.rows[:limit], "row_count": len(qr.rows),
    }
