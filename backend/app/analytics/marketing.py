"""
Marketing analytics: coupon/campaign effectiveness and channel efficiency
(blended CAC, ROAS, cost-per-install).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.analytics.filters import Filters
from app.analytics.query import run_query


# --------------------------------------------------------------------------- #
#  Coupon / campaign effectiveness
# --------------------------------------------------------------------------- #
def coupon_effectiveness(db: Session, filters: Filters) -> dict:
    clause, params, expanding = filters.render()

    # Baseline (non-coupon) economics for comparison.
    baseline = run_query(db, """
        SELECT
            COUNT(*) AS orders,
            COALESCE(AVG(o.subtotal),0)            AS aov,
            COALESCE(AVG(o.contribution_margin),0) AS avg_margin
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE o.status='delivered' AND o.coupon_id IS NULL{filters}
    """.format(filters=clause), params, expanding).first() or {}

    sql = """
    SELECT
        o.coupon_id,
        cp.code                AS code,
        cp.campaign_name       AS campaign_name,
        cp.discount_type       AS discount_type,
        cp.target_segment      AS target_segment,
        COUNT(*)                                        AS redemptions,
        COUNT(DISTINCT o.customer_id)                   AS unique_customers,
        SUM(CASE WHEN o.is_first_order THEN 1 ELSE 0 END) AS new_customer_orders,
        COALESCE(SUM(o.discount_amount),0)              AS discount_given,
        COALESCE(SUM(o.subtotal),0)                     AS gmv,
        COALESCE(SUM(o.net_revenue),0)                  AS net_revenue,
        COALESCE(SUM(o.contribution_margin),0)          AS contribution_margin,
        COALESCE(AVG(o.subtotal),0)                     AS aov,
        COALESCE(AVG(o.contribution_margin),0)          AS avg_margin
    FROM orders o
    JOIN coupons cp   ON cp.id = o.coupon_id
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE o.status='delivered' AND o.coupon_id IS NOT NULL{filters}
    GROUP BY o.coupon_id, cp.code, cp.campaign_name, cp.discount_type, cp.target_segment
    ORDER BY net_revenue DESC
    """.format(filters=clause)
    qr = run_query(db, sql, params, expanding)

    coupons = []
    for r in qr.rows:
        discount = float(r["discount_given"]) or 0
        margin = float(r["contribution_margin"])
        coupons.append({
            "coupon_id": r["coupon_id"],
            "code": r["code"],
            "campaign_name": r["campaign_name"],
            "discount_type": r["discount_type"],
            "target_segment": r["target_segment"],
            "redemptions": r["redemptions"],
            "unique_customers": r["unique_customers"],
            "new_customer_orders": r["new_customer_orders"] or 0,
            "discount_given": round(discount, 2),
            "gmv": round(float(r["gmv"]), 2),
            "net_revenue": round(float(r["net_revenue"]), 2),
            "contribution_margin": round(margin, 2),
            "aov": round(float(r["aov"]), 2),
            "avg_margin_per_order": round(float(r["avg_margin"]), 2),
            # Return on discount spend: contribution margin generated per ₹ of discount.
            "margin_per_discount_rupee": round(margin / discount, 2) if discount else None,
            "discount_as_pct_of_gmv": round(discount / float(r["gmv"]) * 100, 1) if float(r["gmv"]) else 0,
        })

    # Roll campaigns up (multiple city coupons share a campaign_name).
    campaigns: dict[str, dict] = {}
    for c in coupons:
        key = c["campaign_name"]
        agg = campaigns.setdefault(key, {
            "campaign_name": key, "redemptions": 0, "discount_given": 0.0,
            "net_revenue": 0.0, "contribution_margin": 0.0, "new_customer_orders": 0,
        })
        agg["redemptions"] += c["redemptions"]
        agg["discount_given"] += c["discount_given"]
        agg["net_revenue"] += c["net_revenue"]
        agg["contribution_margin"] += c["contribution_margin"]
        agg["new_customer_orders"] += c["new_customer_orders"]
    campaign_rows = []
    for a in campaigns.values():
        a["margin_per_discount_rupee"] = round(a["contribution_margin"] / a["discount_given"], 2) if a["discount_given"] else None
        a["discount_given"] = round(a["discount_given"], 2)
        a["net_revenue"] = round(a["net_revenue"], 2)
        a["contribution_margin"] = round(a["contribution_margin"], 2)
        campaign_rows.append(a)
    campaign_rows.sort(key=lambda x: x["contribution_margin"], reverse=True)

    return {
        "baseline_non_coupon": {
            "orders": baseline.get("orders", 0),
            "aov": round(float(baseline.get("aov") or 0), 2),
            "avg_margin_per_order": round(float(baseline.get("avg_margin") or 0), 2),
        },
        "coupons": coupons,
        "campaigns": campaign_rows,
        "sql": qr.sql,
        "execution_ms": qr.execution_ms,
    }


# --------------------------------------------------------------------------- #
#  Channel efficiency: blended CAC / ROAS / CPI
# --------------------------------------------------------------------------- #
def marketing_efficiency(db: Session, filters: Filters) -> dict:
    # Monthly spend + installs by channel.
    spend_sql = """
    SELECT DATE_TRUNC('month', month) AS period, channel,
           SUM(spend) AS spend, SUM(installs) AS installs
    FROM marketing_spend
    WHERE month >= :f_start AND month <= :f_end
    GROUP BY DATE_TRUNC('month', month), channel
    ORDER BY period
    """
    spend_rows = run_query(db, spend_sql, {
        "f_start": filters.effective_start, "f_end": filters.effective_end,
    }).rows

    # Monthly new customers + net revenue (blended attribution).
    biz_sql = """
    SELECT DATE_TRUNC('month', o.order_date) AS period,
           COUNT(DISTINCT CASE WHEN o.is_first_order THEN o.customer_id END) AS new_customers,
           COALESCE(SUM(CASE WHEN o.status='delivered' THEN o.net_revenue END),0) AS net_revenue
    FROM orders o
    WHERE o.order_date >= :f_start AND o.order_date <= :f_end
    GROUP BY DATE_TRUNC('month', o.order_date)
    ORDER BY period
    """
    biz_rows = {str(r["period"])[:7]: r for r in run_query(db, biz_sql, {
        "f_start": filters.effective_start, "f_end": filters.effective_end,
    }).rows}

    # Channel totals.
    channel_totals: dict[str, dict] = {}
    monthly_spend: dict[str, float] = {}
    for r in spend_rows:
        month = str(r["period"])[:7]
        ch = r["channel"]
        ct = channel_totals.setdefault(ch, {"channel": ch, "spend": 0.0, "installs": 0})
        ct["spend"] += float(r["spend"] or 0)
        ct["installs"] += int(r["installs"] or 0)
        monthly_spend[month] = monthly_spend.get(month, 0.0) + float(r["spend"] or 0)

    channels = []
    for ct in channel_totals.values():
        channels.append({
            "channel": ct["channel"],
            "spend": round(ct["spend"], 2),
            "installs": ct["installs"],
            "cost_per_install": round(ct["spend"] / ct["installs"], 2) if ct["installs"] else None,
        })
    channels.sort(key=lambda x: x["spend"], reverse=True)

    # Blended monthly CAC / ROAS.
    monthly = []
    for month in sorted(monthly_spend.keys()):
        spend = monthly_spend[month]
        biz = biz_rows.get(month, {})
        new_c = biz.get("new_customers") or 0
        net_rev = float(biz.get("net_revenue") or 0)
        monthly.append({
            "period": month,
            "spend": round(spend, 2),
            "new_customers": new_c,
            "net_revenue": round(net_rev, 2),
            "blended_cac": round(spend / new_c, 2) if new_c else None,
            "roas": round(net_rev / spend, 2) if spend else None,
        })

    total_spend = sum(c["spend"] for c in channels)
    total_new = sum(m["new_customers"] for m in monthly)
    total_rev = sum(m["net_revenue"] for m in monthly)
    return {
        "channels": channels,
        "monthly": monthly,
        "summary": {
            "total_spend": round(total_spend, 2),
            "total_new_customers": total_new,
            "blended_cac": round(total_spend / total_new, 2) if total_new else None,
            "blended_roas": round(total_rev / total_spend, 2) if total_spend else None,
        },
        "sql": spend_sql.strip(),
    }
