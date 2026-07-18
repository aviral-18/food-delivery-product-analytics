"""
Operations analytics: delivery performance, delay root-cause decomposition,
cancellation analysis, refund analysis, and peak-hour demand.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.analytics.filters import Filters
from app.analytics.query import run_query


def _f(filters: Filters):
    return filters.render()


# --------------------------------------------------------------------------- #
#  Delivery operations
# --------------------------------------------------------------------------- #
def delivery_operations(db: Session, filters: Filters) -> dict:
    clause, params, expanding = _f(filters)

    overall_sql = """
    SELECT
        COUNT(*)                                                    AS delivered_orders,
        AVG(o.delivery_minutes)                                     AS avg_delivery_minutes,
        AVG(o.prep_minutes)                                         AS avg_prep_minutes,
        AVG(o.distance_km)                                          AS avg_distance_km,
        SUM(CASE WHEN o.is_late THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS late_rate,
        AVG(o.delivery_rating)                                      AS avg_delivery_rating
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE o.status = 'delivered'{filters}
    """.format(filters=clause)
    overall = run_query(db, overall_sql, params, expanding).first() or {}

    by_city_sql = """
    SELECT
        o.city_id,
        COUNT(*)                                                    AS delivered_orders,
        AVG(o.delivery_minutes)                                     AS avg_delivery_minutes,
        SUM(CASE WHEN o.is_late THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS late_rate
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE o.status = 'delivered'{filters}
    GROUP BY o.city_id
    ORDER BY late_rate DESC
    """.format(filters=clause)
    by_city = run_query(db, by_city_sql, params, expanding).rows

    dist_sql = """
    SELECT
        CASE
            WHEN o.delivery_minutes < 20 THEN '<20'
            WHEN o.delivery_minutes < 30 THEN '20-30'
            WHEN o.delivery_minutes < 40 THEN '30-40'
            WHEN o.delivery_minutes < 50 THEN '40-50'
            WHEN o.delivery_minutes < 60 THEN '50-60'
            ELSE '60+'
        END AS bucket,
        COUNT(*) AS orders
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE o.status = 'delivered'{filters}
    GROUP BY bucket
    """.format(filters=clause)
    dist_rows = run_query(db, dist_sql, params, expanding).rows
    order = ["<20", "20-30", "30-40", "40-50", "50-60", "60+"]
    dist = sorted(dist_rows, key=lambda x: order.index(x["bucket"]) if x["bucket"] in order else 99)

    return {
        "overall": {
            "delivered_orders": overall.get("delivered_orders", 0),
            "avg_delivery_minutes": round(float(overall.get("avg_delivery_minutes") or 0), 1),
            "avg_prep_minutes": round(float(overall.get("avg_prep_minutes") or 0), 1),
            "avg_distance_km": round(float(overall.get("avg_distance_km") or 0), 2),
            "late_rate": round(float(overall.get("late_rate") or 0), 4),
            "avg_delivery_rating": round(float(overall.get("avg_delivery_rating") or 0), 2),
        },
        "by_city": by_city,
        "delivery_time_distribution": dist,
        "sql": overall_sql.strip(),
    }


# --------------------------------------------------------------------------- #
#  Delay root-cause analysis
# --------------------------------------------------------------------------- #
def delivery_delay_root_cause(db: Session, filters: Filters) -> dict:
    clause, params, expanding = _f(filters)

    # Time decomposition: prep vs travel vs residual (wait + weather + partner).
    decomp_sql = """
    SELECT
        AVG(o.prep_minutes)                              AS avg_prep,
        AVG(o.delivery_minutes)                          AS avg_total,
        AVG(o.distance_km)                               AS avg_distance,
        AVG(o.delivery_minutes - o.prep_minutes)         AS avg_travel_and_wait
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE o.status = 'delivered'{filters}
    """.format(filters=clause)
    decomp = run_query(db, decomp_sql, params, expanding).first() or {}

    def breakdown(dim_sql: str, label: str):
        sql = """
        SELECT {dim} AS dimension,
               COUNT(*) AS delivered_orders,
               AVG(o.delivery_minutes) AS avg_delivery_minutes,
               AVG(o.prep_minutes) AS avg_prep_minutes,
               SUM(CASE WHEN o.is_late THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS late_rate
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE o.status = 'delivered'{filters}
        GROUP BY {dim}
        ORDER BY late_rate DESC
        """.format(dim=dim_sql, filters=clause)
        return run_query(db, sql, params, expanding).rows

    by_weather = breakdown("o.weather", "weather")
    by_daypart = breakdown("o.day_part", "day_part")
    by_city = breakdown("o.city_id", "city")
    dist_bucket = breakdown(
        "CASE WHEN o.distance_km < 2 THEN '<2km' WHEN o.distance_km < 4 THEN '2-4km' "
        "WHEN o.distance_km < 6 THEN '4-6km' WHEN o.distance_km < 8 THEN '6-8km' ELSE '8km+' END",
        "distance",
    )

    avg_prep = float(decomp.get("avg_prep") or 0)
    avg_total = float(decomp.get("avg_total") or 0)
    prep_share = round(avg_prep / avg_total * 100, 1) if avg_total else 0

    return {
        "decomposition": {
            "avg_prep_minutes": round(avg_prep, 1),
            "avg_travel_and_wait_minutes": round(float(decomp.get("avg_travel_and_wait") or 0), 1),
            "avg_total_minutes": round(avg_total, 1),
            "prep_share_of_total_pct": prep_share,
            "avg_distance_km": round(float(decomp.get("avg_distance") or 0), 2),
        },
        "late_rate_by_weather": by_weather,
        "late_rate_by_day_part": by_daypart,
        "late_rate_by_city": by_city,
        "late_rate_by_distance": dist_bucket,
        "sql": decomp_sql.strip(),
    }


# --------------------------------------------------------------------------- #
#  Cancellation analysis
# --------------------------------------------------------------------------- #
def cancellation_analysis(db: Session, filters: Filters) -> dict:
    clause, params, expanding = _f(filters)

    overall = run_query(db, """
        SELECT COUNT(*) AS total_orders,
               SUM(CASE WHEN o.status='cancelled' THEN 1 ELSE 0 END) AS cancelled_orders
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE 1=1{filters}
    """.format(filters=clause), params, expanding).first() or {}

    by_reason = run_query(db, """
        SELECT o.cancellation_reason AS reason, COUNT(*) AS orders
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE o.status='cancelled'{filters}
        GROUP BY o.cancellation_reason
        ORDER BY orders DESC
    """.format(filters=clause), params, expanding).rows

    by_city = run_query(db, """
        SELECT o.city_id,
               COUNT(*) AS total_orders,
               SUM(CASE WHEN o.status='cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
               SUM(CASE WHEN o.status='cancelled' THEN 1 ELSE 0 END)*1.0/COUNT(*) AS cancel_rate
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE 1=1{filters}
        GROUP BY o.city_id
        ORDER BY cancel_rate DESC
    """.format(filters=clause), params, expanding).rows

    total = overall.get("total_orders") or 0
    cancelled = overall.get("cancelled_orders") or 0
    return {
        "total_orders": total,
        "cancelled_orders": cancelled,
        "cancellation_rate": round(cancelled / total, 4) if total else 0,
        "by_reason": by_reason,
        "by_city": by_city,
        "sql": "SELECT cancellation_reason, COUNT(*) ... WHERE status='cancelled' GROUP BY reason",
    }


# --------------------------------------------------------------------------- #
#  Refund analysis
# --------------------------------------------------------------------------- #
def refund_analysis(db: Session, filters: Filters) -> dict:
    clause, params, expanding = _f(filters)

    overall = run_query(db, """
        SELECT COUNT(*) AS delivered_orders,
               SUM(CASE WHEN o.is_refunded THEN 1 ELSE 0 END) AS refunded_orders,
               COALESCE(SUM(o.refund_amount),0) AS refund_value,
               COALESCE(SUM(o.subtotal),0) AS gmv
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE o.status='delivered'{filters}
    """.format(filters=clause), params, expanding).first() or {}

    by_reason = run_query(db, """
        SELECT o.refund_reason AS reason, COUNT(*) AS orders,
               COALESCE(SUM(o.refund_amount),0) AS refund_value
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE o.status='delivered' AND o.is_refunded{filters}
        GROUP BY o.refund_reason
        ORDER BY orders DESC
    """.format(filters=clause), params, expanding).rows

    late_vs_ontime = run_query(db, """
        SELECT o.is_late AS is_late,
               COUNT(*) AS delivered_orders,
               SUM(CASE WHEN o.is_refunded THEN 1 ELSE 0 END)*1.0/COUNT(*) AS refund_rate
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE o.status='delivered'{filters}
        GROUP BY o.is_late
    """.format(filters=clause), params, expanding).rows

    delivered = overall.get("delivered_orders") or 0
    refunded = overall.get("refunded_orders") or 0
    return {
        "delivered_orders": delivered,
        "refunded_orders": refunded,
        "refund_rate": round(refunded / delivered, 4) if delivered else 0,
        "refund_value": round(float(overall.get("refund_value") or 0), 2),
        "refund_value_pct_of_gmv": round(float(overall.get("refund_value") or 0) / float(overall.get("gmv") or 1) * 100, 2),
        "by_reason": by_reason,
        "refund_rate_late_vs_ontime": late_vs_ontime,
        "sql": "SELECT refund_reason, COUNT(*), SUM(refund_amount) ... WHERE is_refunded GROUP BY reason",
    }


# --------------------------------------------------------------------------- #
#  Peak-hour analytics
# --------------------------------------------------------------------------- #
def peak_hour_analytics(db: Session, filters: Filters) -> dict:
    clause, params, expanding = _f(filters)

    heat_sql = """
    SELECT
        EXTRACT(DOW FROM o.order_datetime)  AS dow,
        EXTRACT(HOUR FROM o.order_datetime) AS hour,
        COUNT(*)                            AS orders,
        COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.net_revenue END),0) AS net_revenue
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE 1=1{filters}
    GROUP BY EXTRACT(DOW FROM o.order_datetime), EXTRACT(HOUR FROM o.order_datetime)
    ORDER BY dow, hour
    """.format(filters=clause)
    rows = run_query(db, heat_sql, params, expanding).rows
    heatmap = [{
        "dow": int(r["dow"]), "hour": int(r["hour"]),
        "orders": int(r["orders"]), "net_revenue": round(float(r["net_revenue"] or 0), 2),
    } for r in rows]

    by_daypart = run_query(db, """
        SELECT o.day_part AS day_part, COUNT(*) AS orders,
               COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.net_revenue END),0) AS net_revenue,
               COALESCE(AVG(CASE WHEN o.status='delivered' THEN o.contribution_margin END),0) AS avg_margin
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE 1=1{filters}
        GROUP BY o.day_part
        ORDER BY orders DESC
    """.format(filters=clause), params, expanding).rows

    peak = max(heatmap, key=lambda x: x["orders"]) if heatmap else None
    return {"heatmap": heatmap, "by_day_part": by_daypart, "peak_slot": peak, "sql": heat_sql.strip()}
