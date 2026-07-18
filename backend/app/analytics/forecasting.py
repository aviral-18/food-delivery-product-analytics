"""
Lightweight time-series forecasting.

A deliberately simple, explainable model: ordinary-least-squares linear trend on
the monthly series plus an additive month-of-year seasonal component, with a
naive prediction band from the in-sample residual spread. No heavy dependencies
-- the goal is a defensible directional forecast a PM can reason about, clearly
labelled as an estimate.
"""
from __future__ import annotations

from datetime import date

import numpy as np
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.analytics.filters import Filters
from app.analytics.query import run_query

_METRICS = {
    "net_revenue": "SUM(CASE WHEN o.status='delivered' THEN o.net_revenue END)",
    "gmv": "SUM(CASE WHEN o.status='delivered' THEN o.subtotal END)",
    "orders": "COUNT(*)",
    "delivered_orders": "SUM(CASE WHEN o.status='delivered' THEN 1 ELSE 0 END)",
}


def forecast(db: Session, filters: Filters, metric: str = "net_revenue", horizon: int = 3) -> dict:
    metric = metric if metric in _METRICS else "net_revenue"
    clause, params, expanding = filters.render()
    sql = """
    SELECT DATE_TRUNC('month', o.order_date) AS period, COALESCE({expr}, 0) AS value
    FROM orders o
    JOIN restaurants r ON r.id = o.restaurant_id
    JOIN customers   c ON c.id = o.customer_id
    WHERE 1=1{filters}
    GROUP BY DATE_TRUNC('month', o.order_date)
    ORDER BY period
    """.format(expr=_METRICS[metric], filters=clause)
    qr = run_query(db, sql, params, expanding)
    rows = qr.rows
    if len(rows) < 4:
        return {"metric": metric, "history": [], "forecast": [], "sql": qr.sql,
                "note": "Not enough history to forecast."}

    periods = [str(r["period"])[:7] for r in rows]
    values = np.array([float(r["value"] or 0) for r in rows], dtype=float)
    x = np.arange(len(values))

    # Linear trend via least squares.
    slope, intercept = np.polyfit(x, values, 1)
    trend = intercept + slope * x

    # Additive month-of-year seasonal component.
    months = np.array([int(p[5:7]) for p in periods])
    resid = values - trend
    seasonal = {m: float(resid[months == m].mean()) for m in range(1, 13) if (months == m).any()}
    fitted = trend + np.array([seasonal.get(m, 0.0) for m in months])
    residual_std = float(np.std(values - fitted))

    history = [{"period": p, "value": round(float(v), 2), "fitted": round(float(f), 2)}
               for p, v, f in zip(periods, values, fitted)]

    last = date.fromisoformat(periods[-1] + "-01")
    forecast_pts = []
    for h in range(1, horizon + 1):
        fx = len(values) - 1 + h
        fmonth = last + relativedelta(months=h)
        m = fmonth.month
        point = intercept + slope * fx + seasonal.get(m, 0.0)
        forecast_pts.append({
            "period": fmonth.strftime("%Y-%m"),
            "forecast": round(max(0.0, float(point)), 2),
            "lower": round(max(0.0, float(point - 1.96 * residual_std)), 2),
            "upper": round(float(point + 1.96 * residual_std), 2),
        })

    return {
        "metric": metric,
        "history": history,
        "forecast": forecast_pts,
        "model": {
            "type": "linear_trend + monthly_seasonality",
            "monthly_slope": round(float(slope), 2),
            "residual_std": round(residual_std, 2),
            "confidence": "95% band (±1.96σ of residuals)",
        },
        "sql": qr.sql,
    }
