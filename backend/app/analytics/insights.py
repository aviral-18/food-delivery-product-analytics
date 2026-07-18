"""
AI Product Insights engine.

Deterministic, rule-based narrative generation in Product-Manager language.
Each generator consumes the *computed* metrics for a page and emits structured
insights (trend / anomaly / root-cause / risk / opportunity / recommendation /
A-B-test idea). This is intentionally explainable — every sentence is traceable
to a number, which is exactly what you want to defend in a review. It is not an
LLM; it is an analytics narrative layer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

from sqlalchemy.orm import Session

from app.analytics import catalog, customers, executive, marketing, operations
from app.analytics.filters import Filters


@dataclass
class Insight:
    type: str          # summary | trend | anomaly | root_cause | risk | opportunity | recommendation | ab_test
    severity: str      # positive | low | medium | high
    title: str
    detail: str
    metric: str | None = None


def _fmt_money(x: float) -> str:
    x = float(x)
    if abs(x) >= 1e7:
        return f"Rs {x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"Rs {x/1e5:.2f} L"
    return f"Rs {x:,.0f}"


def _pct(x: float) -> str:
    return f"{x*100:.1f}%"


# --------------------------------------------------------------------------- #
#  Executive
# --------------------------------------------------------------------------- #
def executive_insights(db: Session, filters: Filters) -> list[Insight]:
    out: list[Insight] = []
    health = executive.health_index(db, filters)
    kpi = executive.kpi_summary(db, filters)["raw"]

    out.append(Insight(
        "summary", "positive" if health["overall_score"] >= 65 else "medium",
        f"Product Health Index: {health['overall_score']}/100 (Grade {health['grade']})",
        "Weighted across growth, retention, unit economics, experience and operations. "
        + "Weakest pillar: "
        + min(health["subscores"], key=health["subscores"].get)
        + f" ({min(health['subscores'].values())}/100).",
        metric="health_index",
    ))

    g = health["drivers"]["net_revenue_mom_growth_pct"]
    out.append(Insight(
        "trend", "positive" if g >= 0 else "high",
        f"Net revenue is {'growing' if g >= 0 else 'contracting'} at {g:.1f}% MoM",
        f"Recent months average {g:.1f}% month-over-month net-revenue change. "
        + ("Momentum is healthy." if g >= 5 else "Growth is decelerating — investigate acquisition quality and retention."),
        metric="net_revenue",
    ))

    if kpi["contribution_margin_pct"] < 0.05:
        out.append(Insight(
            "risk", "high",
            f"Thin unit economics: contribution margin is only {_pct(kpi['contribution_margin_pct'])} of GMV",
            f"Discounts ({_fmt_money(kpi['discount_given'])}) and delivery costs are compressing margin. "
            "Consider raising free-delivery thresholds or trimming the least efficient coupon campaigns.",
            metric="contribution_margin_pct",
        ))

    if kpi["late_delivery_rate"] > 0.22:
        out.append(Insight(
            "risk", "medium",
            f"On-time delivery is a weak spot: {_pct(kpi['late_delivery_rate'])} of orders breach SLA",
            "Late deliveries strongly predict refunds and churn (see Delivery Delay Root Cause). "
            "Prioritise the worst cities and peak dinner slots.",
            metric="late_delivery_rate",
        ))
    return out


# --------------------------------------------------------------------------- #
#  Retention / cohorts
# --------------------------------------------------------------------------- #
def retention_insights(db: Session, filters: Filters) -> list[Insight]:
    out: list[Insight] = []
    coh = customers.cohort_retention(db, filters)
    cohorts = coh["cohorts"]
    if len(cohorts) >= 6:
        def m1(c):
            v = next((x["retention_pct"] for x in c["values"] if x["period"] == 1), None)
            return v
        early = [m1(c) for c in cohorts[:3] if m1(c) is not None]
        recent = [m1(c) for c in cohorts[-4:-1] if m1(c) is not None]
        if early and recent:
            e, r = sum(early) / len(early), sum(recent) / len(recent)
            if r < e - 3:
                out.append(Insight(
                    "root_cause", "high",
                    f"Month-1 retention is deteriorating: {e:.0f}% (early cohorts) -> {r:.0f}% (recent cohorts)",
                    "Newer cohorts come back less. This aligns with a rising paid-acquisition mix bringing "
                    "lower-intent users, and reduced first-order incentives in some markets. "
                    "Segment retention by acquisition channel and by city tier to confirm.",
                    metric="retention_m1",
                ))
    clv = customers.clv_analysis(db, filters)
    ch = clv.get("by_channel", [])
    if len(ch) >= 2:
        best, worst = ch[0], ch[-1]
        out.append(Insight(
            "opportunity", "medium",
            f"'{best['acquisition_channel']}' users are worth {best['avg_clv'] / max(worst['avg_clv'],1):.1f}x more than '{worst['acquisition_channel']}'",
            f"Average historical value: {_fmt_money(best['avg_clv'])} vs {_fmt_money(worst['avg_clv'])}. "
            "Reallocate acquisition budget toward higher-LTV channels and tighten targeting on the weakest.",
            metric="clv_by_channel",
        ))
    out.append(Insight(
        "ab_test", "low",
        "Suggested experiment: second-order nudge for first-time buyers",
        "Trigger a personalised 'order #2' offer 72h after first delivery for paid-acquired users. "
        "Primary metric: first-to-second-order conversion; guardrail: contribution margin per order.",
    ))
    return out


# --------------------------------------------------------------------------- #
#  Coupons
# --------------------------------------------------------------------------- #
def coupon_insights(db: Session, filters: Filters) -> list[Insight]:
    out: list[Insight] = []
    ce = marketing.coupon_effectiveness(db, filters)
    camps = [c for c in ce["campaigns"] if c["redemptions"] >= 20]
    if len(camps) >= 2:
        by_eff = sorted(camps, key=lambda c: (c["margin_per_discount_rupee"] or -99))
        worst, best = by_eff[0], by_eff[-1]
        out.append(Insight(
            "root_cause", "high",
            f"'{worst['campaign_name']}' is the least efficient campaign",
            f"It returns {worst['margin_per_discount_rupee']} of margin per Rs 1 of discount "
            f"({worst['redemptions']:,} redemptions, {_fmt_money(worst['discount_given'])} given) versus "
            f"'{best['campaign_name']}' at {best['margin_per_discount_rupee']}. "
            "More orders did not mean more profit — consider capping or retiring it.",
            metric="margin_per_discount_rupee",
        ))
    base = ce["baseline_non_coupon"]
    hi_disc = [c for c in ce["coupons"] if c["discount_as_pct_of_gmv"] > 25 and c["redemptions"] >= 20]
    if hi_disc:
        c = max(hi_disc, key=lambda x: x["redemptions"])
        out.append(Insight(
            "risk", "medium",
            f"Deep discounting on '{c['code']}': {c['discount_as_pct_of_gmv']}% of GMV given back",
            f"Its average margin per order ({_fmt_money(c['avg_margin_per_order'])}) trails the non-coupon "
            f"baseline ({_fmt_money(base['avg_margin_per_order'])}). Test a lower cap or a higher minimum order value.",
            metric="discount_as_pct_of_gmv",
        ))
    out.append(Insight(
        "ab_test", "low",
        "Suggested experiment: minimum-order-value uplift on the weakest campaign",
        "Raise the min-order threshold by ~15% for the least efficient campaign and measure impact on "
        "redemptions, AOV and contribution margin per order over 3 weeks.",
    ))
    return out


# --------------------------------------------------------------------------- #
#  Delivery operations
# --------------------------------------------------------------------------- #
def delivery_insights(db: Session, filters: Filters) -> list[Insight]:
    out: list[Insight] = []
    rc = operations.delivery_delay_root_cause(db, filters)
    d = rc["decomposition"]
    out.append(Insight(
        "root_cause", "medium",
        f"Restaurant prep time is {d['prep_share_of_total_pct']}% of total delivery time",
        f"Average order takes {d['avg_total_minutes']} min: {d['avg_prep_minutes']} min prep + "
        f"{d['avg_travel_and_wait_minutes']} min travel/wait. "
        + ("Prep is the dominant lever — work with slow kitchens on batching and auto-accept."
           if d['prep_share_of_total_pct'] > 45 else "Last-mile is the dominant lever — review fleet density."),
        metric="prep_share",
    ))
    w = rc["late_rate_by_weather"]
    if w:
        worst = max(w, key=lambda x: x["late_rate"])
        best = min(w, key=lambda x: x["late_rate"])
        out.append(Insight(
            "trend", "medium",
            f"Weather swings SLA sharply: {_pct(worst['late_rate'])} late in '{worst['dimension']}' vs {_pct(best['late_rate'])} in '{best['dimension']}'",
            "Dynamically extend promised ETAs and add surge partner incentives during rain/storm/fog "
            "to protect the on-time promise.",
            metric="late_rate_by_weather",
        ))
    city = rc["late_rate_by_city"]
    if city:
        worst = max(city, key=lambda x: x["late_rate"])
        out.append(Insight(
            "risk", "medium",
            f"City {worst['dimension']} has the worst SLA at {_pct(worst['late_rate'])} late",
            "Concentrate operational fixes here first; it likely drives an outsized share of refunds and churn.",
            metric="late_rate_by_city",
        ))
    return out


# --------------------------------------------------------------------------- #
#  City performance
# --------------------------------------------------------------------------- #
def city_insights(db: Session, filters: Filters) -> list[Insight]:
    out: list[Insight] = []
    cities = catalog.city_performance(db, filters)["cities"]
    with_roas = [c for c in cities if c["roas"] is not None]
    if with_roas:
        best = max(with_roas, key=lambda x: x["roas"])
        worst = min(with_roas, key=lambda x: x["roas"])
        out.append(Insight(
            "opportunity", "medium",
            f"Marketing efficiency varies widely: City {best['city_id']} ROAS {best['roas']} vs City {worst['city_id']} {worst['roas']}",
            f"Shift incremental budget toward City {best['city_id']} (CAC {_fmt_money(best['cac'] or 0)}) and "
            f"diagnose City {worst['city_id']} before scaling spend there.",
            metric="roas",
        ))
    return out


# --------------------------------------------------------------------------- #
#  Dispatcher
# --------------------------------------------------------------------------- #
_GENERATORS: dict[str, Callable[[Session, Filters], list[Insight]]] = {
    "executive": executive_insights,
    "retention": retention_insights,
    "cohorts": retention_insights,
    "clv": retention_insights,
    "coupons": coupon_insights,
    "delivery": delivery_insights,
    "cancellation": delivery_insights,
    "refunds": delivery_insights,
    "city": city_insights,
}


def generate_insights(db: Session, filters: Filters, page: str = "executive") -> dict:
    gen = _GENERATORS.get(page, executive_insights)
    insights = gen(db, filters)
    return {
        "page": page,
        "count": len(insights),
        "insights": [asdict(i) for i in insights],
    }


def available_pages() -> list[str]:
    return sorted(_GENERATORS.keys())
