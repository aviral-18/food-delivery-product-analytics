"""
Customer analytics: acquisition cohorts, retention matrix, RFM segmentation,
CLV, repeat-purchase behaviour, order-frequency distribution, and the customer
journey funnel.

Heavy aggregation is done in SQL; matrix/segment shaping is finished in pandas
(a standard warehouse + notebook division of labour).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.filters import Filters
from app.analytics.query import run_query


def _frame(db: Session, sql: str, params: dict, expanding) -> tuple[pd.DataFrame, str]:
    qr = run_query(db, sql, params, expanding)
    return pd.DataFrame(qr.rows, columns=qr.columns), qr.sql


# --------------------------------------------------------------------------- #
#  Cohort retention
# --------------------------------------------------------------------------- #
COHORT_SQL = """
SELECT
    o.customer_id,
    DATE_TRUNC('month', o.order_date) AS order_month
FROM orders o
JOIN restaurants r ON r.id = o.restaurant_id
JOIN customers   c ON c.id = o.customer_id
WHERE o.status = 'delivered'{filters}
GROUP BY o.customer_id, DATE_TRUNC('month', o.order_date)
ORDER BY o.customer_id, order_month
"""


def cohort_retention(db: Session, filters: Filters, max_periods: int = 13) -> dict:
    clause, params, expanding = filters.render()
    df, sql = _frame(db, COHORT_SQL.format(filters=clause), params, expanding)
    if df.empty:
        return {"cohorts": [], "retention_curve": [], "sql": sql}

    df["order_month"] = pd.to_datetime(df["order_month"])
    first = df.groupby("customer_id")["order_month"].min().rename("cohort")
    df = df.join(first, on="customer_id")
    df["idx"] = (
        (df["order_month"].dt.year - df["cohort"].dt.year) * 12
        + (df["order_month"].dt.month - df["cohort"].dt.month)
    )
    sizes = df.groupby("cohort")["customer_id"].nunique()
    pivot = (
        df.groupby(["cohort", "idx"])["customer_id"].nunique()
        .unstack(fill_value=0)
        .sort_index()
    )

    cohorts = []
    for cohort_month, row in pivot.iterrows():
        size = int(sizes[cohort_month])
        values = []
        for k in range(min(max_periods, pivot.columns.max() + 1)):
            count = int(row.get(k, 0))
            values.append({
                "period": k,
                "customers": count,
                "retention_pct": round(count / size * 100, 1) if size else 0.0,
            })
        cohorts.append({
            "cohort": cohort_month.strftime("%Y-%m"),
            "size": size,
            "values": values,
        })

    # Average retention curve (size-weighted) across cohorts per period index.
    curve = []
    for k in range(min(max_periods, pivot.columns.max() + 1)):
        total_size = 0
        retained = 0
        for cohort_month in pivot.index:
            size = int(sizes[cohort_month])
            total_size += size
            retained += int(pivot.loc[cohort_month].get(k, 0))
        curve.append({
            "period": k,
            "retention_pct": round(retained / total_size * 100, 1) if total_size else 0.0,
        })
    return {"cohorts": cohorts, "retention_curve": curve, "sql": sql}


# --------------------------------------------------------------------------- #
#  RFM segmentation
# --------------------------------------------------------------------------- #
RFM_SQL = """
SELECT
    o.customer_id,
    c.acquisition_channel,
    c.city_id,
    MAX(o.order_date)              AS last_order_date,
    COUNT(*)                       AS frequency,
    SUM(o.subtotal)                AS monetary,
    SUM(o.net_revenue)             AS net_revenue
FROM orders o
JOIN restaurants r ON r.id = o.restaurant_id
JOIN customers   c ON c.id = o.customer_id
WHERE o.status = 'delivered'{filters}
GROUP BY o.customer_id, c.acquisition_channel, c.city_id
"""


def _rfm_segment(r: int, f: int) -> str:
    if r >= 4 and f >= 4:
        return "Champions"
    if r >= 3 and f >= 4:
        return "Loyal Customers"
    if r >= 4 and f == 3:
        return "Potential Loyalist"
    if r >= 4 and f <= 2:
        return "New Customers"
    if r == 3 and f <= 3:
        return "Promising"
    if r == 2 and f >= 4:
        return "Can't Lose Them"
    if r == 2 and f >= 2:
        return "At Risk"
    if r <= 2 and f <= 2:
        return "Hibernating"
    if r <= 1:
        return "Lost"
    return "Needs Attention"


def rfm_segmentation(db: Session, filters: Filters) -> dict:
    clause, params, expanding = filters.render()
    df, sql = _frame(db, RFM_SQL.format(filters=clause), params, expanding)
    if df.empty:
        return {"segments": [], "customers_scored": 0, "sql": sql}

    analysis_end = pd.Timestamp(filters.effective_end)
    df["last_order_date"] = pd.to_datetime(df["last_order_date"])
    df["recency_days"] = (analysis_end - df["last_order_date"]).dt.days.clip(lower=0)
    df["frequency"] = df["frequency"].astype(int)
    df["monetary"] = df["monetary"].astype(float)

    # Quantile scoring (rank-first ensures 5 non-degenerate bins).
    def score(series, ascending=True):
        ranked = series.rank(method="first", ascending=ascending)
        return pd.qcut(ranked, 5, labels=[1, 2, 3, 4, 5]).astype(int)

    df["R"] = score(df["recency_days"], ascending=False)  # recent -> high
    df["F"] = score(df["frequency"], ascending=True)
    df["M"] = score(df["monetary"], ascending=True)
    df["segment"] = [ _rfm_segment(r, f) for r, f in zip(df["R"], df["F"]) ]

    total = len(df)
    seg = df.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_recency_days=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_net_revenue=("net_revenue", "sum"),
    ).reset_index()
    seg = seg.sort_values("total_net_revenue", ascending=False)

    segments = [{
        "segment": row["segment"],
        "customers": int(row["customers"]),
        "share_pct": round(row["customers"] / total * 100, 1),
        "avg_recency_days": round(float(row["avg_recency_days"]), 1),
        "avg_frequency": round(float(row["avg_frequency"]), 2),
        "avg_monetary": round(float(row["avg_monetary"]), 2),
        "total_net_revenue": round(float(row["total_net_revenue"]), 2),
        "revenue_share_pct": round(float(row["total_net_revenue"]) / df["net_revenue"].sum() * 100, 1),
    } for _, row in seg.iterrows()]

    return {
        "customers_scored": total,
        "segments": segments,
        "scatter_sample": _rfm_scatter_sample(df),
        "sql": sql,
    }


def _rfm_scatter_sample(df: pd.DataFrame, n: int = 400) -> list[dict]:
    sample = df.sample(min(n, len(df)), random_state=1)
    return [{
        "customer_id": int(row["customer_id"]),
        "recency_days": int(row["recency_days"]),
        "frequency": int(row["frequency"]),
        "monetary": round(float(row["monetary"]), 2),
        "segment": row["segment"],
    } for _, row in sample.iterrows()]


# --------------------------------------------------------------------------- #
#  Customer Lifetime Value
# --------------------------------------------------------------------------- #
CLV_SQL = """
SELECT
    o.customer_id,
    c.acquisition_channel,
    c.city_id,
    c.signup_date,
    COUNT(*)                                   AS orders,
    SUM(o.subtotal)                            AS gmv,
    SUM(o.net_revenue)                         AS net_revenue,
    SUM(o.contribution_margin)                 AS margin,
    MIN(o.order_date)                          AS first_order_date,
    MAX(o.order_date)                          AS last_order_date
FROM orders o
JOIN restaurants r ON r.id = o.restaurant_id
JOIN customers   c ON c.id = o.customer_id
WHERE o.status = 'delivered'{filters}
GROUP BY o.customer_id, c.acquisition_channel, c.city_id, c.signup_date
"""


def clv_analysis(db: Session, filters: Filters) -> dict:
    clause, params, expanding = filters.render()
    df, sql = _frame(db, CLV_SQL.format(filters=clause), params, expanding)
    if df.empty:
        return {"summary": {}, "deciles": [], "by_channel": [], "by_city": [], "sql": sql}

    for col in ("first_order_date", "last_order_date"):
        df[col] = pd.to_datetime(df[col])
    df["orders"] = df["orders"].astype(int)
    df["net_revenue"] = df["net_revenue"].astype(float)
    df["margin"] = df["margin"].astype(float)
    df["lifespan_days"] = (df["last_order_date"] - df["first_order_date"]).dt.days.clip(lower=1)
    df["aov"] = df["gmv"].astype(float) / df["orders"]

    # Simple predictive CLV: avg order margin * expected lifetime orders.
    # Expected future orders scaled by observed frequency (orders/active month).
    df["active_months"] = (df["lifespan_days"] / 30.0).clip(lower=1)
    df["orders_per_month"] = df["orders"] / df["active_months"]
    horizon_months = 12
    df["predicted_clv"] = (df["margin"] / df["orders"]) * df["orders_per_month"] * horizon_months

    hist = df["net_revenue"]
    summary = {
        "customers": int(len(df)),
        "avg_historical_clv_net_revenue": round(float(hist.mean()), 2),
        "median_historical_clv": round(float(hist.median()), 2),
        "avg_predicted_12m_clv_margin": round(float(df["predicted_clv"].mean()), 2),
        "avg_orders_per_customer": round(float(df["orders"].mean()), 2),
        "avg_aov": round(float(df["aov"].mean()), 2),
        "top_10pct_revenue_share": round(
            float(hist.nlargest(max(1, len(df) // 10)).sum() / hist.sum() * 100), 1
        ),
    }

    # Deciles by historical net revenue.
    df = df.sort_values("net_revenue", ascending=False).reset_index(drop=True)
    df["decile"] = np.clip(np.floor(np.arange(len(df)) / len(df) * 10).astype(int), 0, 9) + 1
    dec = df.groupby("decile").agg(
        customers=("customer_id", "count"),
        avg_clv=("net_revenue", "mean"),
        total_revenue=("net_revenue", "sum"),
        avg_orders=("orders", "mean"),
    ).reset_index()
    deciles = [{
        "decile": int(row["decile"]),
        "customers": int(row["customers"]),
        "avg_clv": round(float(row["avg_clv"]), 2),
        "total_revenue": round(float(row["total_revenue"]), 2),
        "revenue_share_pct": round(float(row["total_revenue"]) / hist.sum() * 100, 1),
        "avg_orders": round(float(row["avg_orders"]), 2),
    } for _, row in dec.iterrows()]

    by_channel = _clv_group(df, "acquisition_channel")
    by_city = _clv_group(df, "city_id")
    return {
        "summary": summary, "deciles": deciles,
        "by_channel": by_channel, "by_city": by_city, "sql": sql,
    }


def _clv_group(df: pd.DataFrame, key: str) -> list[dict]:
    g = df.groupby(key).agg(
        customers=("customer_id", "count"),
        avg_clv=("net_revenue", "mean"),
        avg_predicted_clv=("predicted_clv", "mean"),
        avg_orders=("orders", "mean"),
    ).reset_index().sort_values("avg_clv", ascending=False)
    return [{
        str(key): (int(row[key]) if key == "city_id" else row[key]),
        "customers": int(row["customers"]),
        "avg_clv": round(float(row["avg_clv"]), 2),
        "avg_predicted_clv": round(float(row["avg_predicted_clv"]), 2),
        "avg_orders": round(float(row["avg_orders"]), 2),
    } for _, row in g.iterrows()]


# --------------------------------------------------------------------------- #
#  Repeat purchase behaviour
# --------------------------------------------------------------------------- #
def repeat_purchase(db: Session, filters: Filters) -> dict:
    clause, params, expanding = filters.render()
    sql = """
    SELECT o.customer_id, o.order_date
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE o.status = 'delivered'{filters}
    ORDER BY o.customer_id, o.order_date
    """.format(filters=clause)
    df, disp = _frame(db, sql, params, expanding)
    if df.empty:
        return {"summary": {}, "order_number_retention": [], "days_between_buckets": [], "sql": disp}

    df["order_date"] = pd.to_datetime(df["order_date"])
    counts = df.groupby("customer_id").size()
    total_customers = len(counts)

    # P(reach order n) — conversion at each step.
    max_n = int(min(10, counts.max()))
    retention = []
    for n in range(1, max_n + 1):
        reached = int((counts >= n).sum())
        retention.append({
            "order_number": n,
            "customers": reached,
            "pct_of_activated": round(reached / total_customers * 100, 1),
            "step_conversion_pct": round(reached / int((counts >= n - 1).sum()) * 100, 1) if n > 1 else 100.0,
        })

    # Days between consecutive orders.
    df["prev"] = df.groupby("customer_id")["order_date"].shift(1)
    gaps = (df["order_date"] - df["prev"]).dt.days.dropna()
    buckets = [(0, 3), (4, 7), (8, 14), (15, 30), (31, 60), (61, 90), (91, 9999)]
    labels = ["0-3d", "4-7d", "8-14d", "15-30d", "31-60d", "61-90d", "90d+"]
    days_between = []
    for (lo, hi), lab in zip(buckets, labels):
        cnt = int(((gaps >= lo) & (gaps <= hi)).sum())
        days_between.append({"bucket": lab, "orders": cnt, "share_pct": round(cnt / len(gaps) * 100, 1) if len(gaps) else 0})

    summary = {
        "activated_customers": total_customers,
        "repeat_customers": int((counts >= 2).sum()),
        "repeat_purchase_rate": round(float((counts >= 2).mean()), 4),
        "first_to_second_conversion": round(float((counts >= 2).sum() / total_customers), 4),
        "avg_orders_per_customer": round(float(counts.mean()), 2),
        "median_days_between_orders": round(float(gaps.median()), 1) if len(gaps) else None,
    }
    return {"summary": summary, "order_number_retention": retention, "days_between_buckets": days_between, "sql": disp}


# --------------------------------------------------------------------------- #
#  Order-frequency distribution
# --------------------------------------------------------------------------- #
def order_frequency(db: Session, filters: Filters) -> dict:
    clause, params, expanding = filters.render()
    sql = """
    SELECT n_orders, COUNT(*) AS customers FROM (
        SELECT o.customer_id, COUNT(*) AS n_orders
        FROM orders o
        JOIN restaurants r ON r.id = o.restaurant_id
        JOIN customers   c ON c.id = o.customer_id
        WHERE o.status = 'delivered'{filters}
        GROUP BY o.customer_id
    ) t
    GROUP BY n_orders
    ORDER BY n_orders
    """.format(filters=clause)
    qr = run_query(db, sql, params, expanding)
    buckets_def = [(1, 1, "1"), (2, 2, "2"), (3, 4, "3-4"), (5, 9, "5-9"), (10, 19, "10-19"), (20, 10**9, "20+")]
    agg = {lab: 0 for *_, lab in buckets_def}
    total = 0
    for row in qr.rows:
        n, cust = int(row["n_orders"]), int(row["customers"])
        total += cust
        for lo, hi, lab in buckets_def:
            if lo <= n <= hi:
                agg[lab] += cust
                break
    distribution = [{"bucket": lab, "customers": agg[lab], "share_pct": round(agg[lab] / total * 100, 1) if total else 0}
                    for *_, lab in buckets_def]
    return {"distribution": distribution, "total_customers": total, "sql": qr.sql}


# --------------------------------------------------------------------------- #
#  Customer journey funnel
# --------------------------------------------------------------------------- #
def customer_journey_funnel(db: Session, filters: Filters) -> dict:
    """Signup -> activation -> 2nd/3rd/5th order -> retained (recent)."""
    clause, params, expanding = filters.render()
    # Signups within window (independent of order filters other than date).
    signup_sql = """
    SELECT COUNT(*) AS signups FROM customers c
    WHERE c.signup_date >= :f_sig_start AND c.signup_date <= :f_sig_end
    """
    signups = run_query(db, signup_sql, {
        "f_sig_start": filters.effective_start, "f_sig_end": filters.effective_end,
    }).scalar or 0

    per_cust_sql = """
    SELECT o.customer_id, COUNT(*) AS n, MAX(o.order_date) AS last_order
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE o.status = 'delivered'{filters}
    GROUP BY o.customer_id
    """.format(filters=clause)
    df, disp = _frame(db, per_cust_sql, params, expanding)

    end = pd.Timestamp(filters.effective_end)
    activated = len(df)
    if activated:
        df["last_order"] = pd.to_datetime(df["last_order"])
        retained = int((df["last_order"] >= (end - pd.Timedelta(days=60))).sum())
    else:
        retained = 0

    def cnt(min_orders):
        return int((df["n"] >= min_orders).sum()) if activated else 0

    stages = [
        {"stage": "Signed up", "customers": int(signups)},
        {"stage": "Placed 1st order (activated)", "customers": activated},
        {"stage": "Placed 2nd order", "customers": cnt(2)},
        {"stage": "Placed 3rd order", "customers": cnt(3)},
        {"stage": "Placed 5th order", "customers": cnt(5)},
        {"stage": "Retained (ordered in last 60d)", "customers": retained},
    ]
    top = stages[0]["customers"] or 1
    for i, s in enumerate(stages):
        s["pct_of_top"] = round(s["customers"] / top * 100, 1)
        prev = stages[i - 1]["customers"] if i > 0 else s["customers"]
        s["step_conversion_pct"] = round(s["customers"] / prev * 100, 1) if prev else 0.0
        s["drop_off_pct"] = round(100 - s["step_conversion_pct"], 1) if i > 0 else 0.0
    return {"stages": stages, "sql": disp}
