# Business Assumptions & Models

Everything that isn't directly observable is modelled with **documented,
defensible assumptions**. This page is the reference for those assumptions so
every number in the platform is traceable.

---

## 1. Unit economics (contribution-margin model)

For each **delivered** order:

```
GMV                 = subtotal (food value)
commission_amount   = subtotal × commission_rate            # 14–26% per restaurant
gross_revenue       = commission_amount + delivery_fee + platform_fee
platform_fee        = ₹6 flat
delivery_fee        = 0 if subtotal ≥ ₹349 else ~₹19 + ₹4/km  (capped ₹15–70)

platform_funded_discount = discount_amount × 60%            # platform funds 60% of coupons
net_revenue         = gross_revenue − platform_funded_discount − refund_amount

delivery_cost       = max(₹25, distance_km × ₹9) × surge    # rider payout
payment_gateway_cost= total_amount × 1.8%   (0 for COD)
support_cost        = ₹35 per support ticket (refunds/complaints)

contribution_margin = net_revenue − delivery_cost − payment_gateway_cost − support_cost
```

Cancelled orders generate **no revenue** (only a small support cost). GST (5%) is a
pass-through and excluded from revenue.

> These parameters live in `app/core/constants.py :: Finance`.

**Why contribution margin?** It's the metric that tells a PM whether *incremental*
orders make or lose money — the right lens for pricing, coupons and delivery-fee
decisions. It is deliberately *thin* (~6–7% of GMV), matching real growth-stage
food-delivery economics.

---

## 2. Synthetic data generation

The dataset is **generative**, not random — each customer has a simulated lifetime:

1. **Signup** — growth-weighted across the 24 months; paid-acquisition share rises
   from 25% → 62% over time.
2. **Activation gate** — `P(activate) = 0.62 + 0.28 × loyalty`. Un-activated
   signups never order (they show up as funnel drop-off).
3. **Order rate** — each active month draws `Poisson(base_freq × seasonality)`
   orders; order days are weighted by weekday, festivals and demand growth.
4. **Churn** — a monthly hazard `≈ 0.40 − 0.26 × loyalty + 0.12 × cohort_recency`
   gives a geometric active lifetime. **Later & paid cohorts churn faster** — this
   is the engine behind the "retention is declining" narrative.

Latent per-customer traits (`loyalty`, `base_monthly_freq`, `price_sensitivity`)
drive behaviour but are **not stored** — the analytics engine must rediscover them
from data, exactly like real life.

### Deliberately-encoded stories to discover
- **Retention decline** — rising paid mix + reduced Tier-2 first-order coupons →
  newer cohorts retain worse.
- **Coupon profitability** — an aggressive % campaign drives orders but returns
  little/negative margin per ₹ of discount; a modest flat campaign is efficient.
- **Delivery delays** — restaurant prep is ~55% of delivery time; weather (storm/fog)
  sharply degrades SLA; late orders drive materially higher refund rates.
- **LTV by channel** — referral/organic customers out-earn paid-acquired ones.

---

## 3. SLA / delivery model

```
delivery_minutes = prep + travel + pickup_wait + weather_penalty + (1−reliability)×12
travel           = distance_km / vehicle_speed × 60
promised_minutes = base_prep + travel + 15   (service buffer)
is_late          = delivery_minutes > promised_minutes
```

Weather delivery penalties (minutes): storm +16, fog +10, rain +8, heat +4.

---

## 4. Product Health Index

A weighted 0–100 composite (graded A–F). Each pillar is normalised to a documented
target band, then combined:

| Pillar | Weight | Signal | 0-point → 100-point band |
|--------|:------:|--------|--------------------------|
| Growth | 22% | Net-revenue MoM growth | 0% → +15% |
| Retention | 22% | Repeat purchase rate | 0% → 70% |
| Unit economics | 20% | Contribution margin % of GMV | −2% → +12% |
| Experience | 18% | Avg rating × (1 − refund penalty) | rating 3.0 → 5.0 |
| Operations | 18% | On-time share + (1 − cancellation) | composite |

---

## 5. Decision Lab elasticities

Directional estimates only — labelled as such in every response. Constants in
`app/analytics/decision_lab.py :: Elasticity`.

| Lever | Assumption |
|-------|-----------|
| Reduce coupon value | Order loss = coupon-share × cut × **0.45** price elasticity; platform saves 60% of the discount; small retention drag. |
| Increase delivery fee | Order change = −(fee / AOV) × **0.60**; ~95% of the fee flows to margin. |
| Improve delivery time | Repeat lift **0.012/min** (capped 6%); modest net fleet cost offset by fewer refunds. |
| Add restaurants | Order lift with diminishing returns (**0.25** supply elasticity). |
| Increase marketing spend | New-customer lift **0.55/unit spend**; CAC dilutes near-term margin. |
| Change free-delivery threshold | ~**0.6%** of orders cross the threshold per ₹; margin up, small volume dip. |

These are **planning heuristics**, not a forecast — the intent is to make the
trade-off structure explicit for a PM conversation.
