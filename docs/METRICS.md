# Metric Definitions

Every metric: what it means, how it's calculated, and the canonical SQL. The SQL
here is PostgreSQL; the live SQL Explorer (`/api/v1/sql/queries`) serves the same
queries and runs them against the database with timing.

> Notation: "delivered orders" = `status = 'delivered'`. Filters (date, city,
> cuisine, …) are applied as an additional `WHERE` clause everywhere.

---

## Growth & engagement

### DAU / WAU / MAU
Distinct customers who placed an order in a day / week / month.
```sql
SELECT COUNT(DISTINCT customer_id)
FROM orders WHERE order_date = :day;               -- DAU (week/month via range)
```

### Repeat Purchase Rate
Share of activated customers with ≥ 2 delivered orders.
```sql
SELECT AVG(CASE WHEN n >= 2 THEN 1.0 ELSE 0 END)
FROM (SELECT customer_id, COUNT(*) n FROM orders
      WHERE status='delivered' GROUP BY customer_id) t;
```

### Retention (cohort)
For each acquisition-month cohort, the % still ordering `k` months later.
Base query pulls (customer, order-month); the matrix is pivoted in pandas.
```sql
SELECT customer_id, DATE_TRUNC('month', order_date) AS order_month
FROM orders WHERE status='delivered'
GROUP BY customer_id, DATE_TRUNC('month', order_date);
```

---

## Revenue & economics

| Metric | Definition |
|--------|-----------|
| **GMV** | Σ `subtotal` of delivered orders (food value) |
| **Gross Revenue** | Σ `commission + delivery_fee + platform_fee` |
| **Net Revenue** | Gross revenue − platform-funded discounts − refunds |
| **Take Rate** | Net revenue ÷ GMV |
| **AOV** | GMV ÷ delivered orders |
| **Contribution Margin** | Net revenue − delivery cost − gateway − support cost |
| **CM %** | Contribution margin ÷ GMV |

```sql
SELECT DATE_TRUNC('month', order_date) AS month,
       SUM(subtotal)      AS gmv,
       SUM(net_revenue)   AS net_revenue,
       ROUND(SUM(net_revenue)/NULLIF(SUM(subtotal),0)*100,2) AS take_rate_pct
FROM orders WHERE status='delivered'
GROUP BY 1 ORDER BY 1;
```

---

## Customer value

### RFM
Per customer: **Recency** (days since last order), **Frequency** (order count),
**Monetary** (spend). Each scored 1–5 by quintile; segments assigned from R×F
(Champions, Loyal, At Risk, Hibernating, Lost, …).

### CLV
- **Historical CLV** = Σ net revenue per customer.
- **Predictive (12-month) CLV** = margin-per-order × orders-per-month × 12.
- Reported with deciles (top-decile revenue concentration) and by acquisition
  channel & city.

---

## Operations

| Metric | Definition |
|--------|-----------|
| **Avg Delivery Time** | Mean `delivery_minutes` (delivered) |
| **Late Delivery %** | Share with `delivery_minutes > promised_minutes` |
| **Cancellation Rate** | Cancelled ÷ total orders |
| **Refund Rate** | Refunded ÷ delivered orders |
| **Delivery Success Rate** | Delivered ÷ total orders |

### Delay root cause
Decomposes delivery time into **prep vs travel/wait**, and reports late-rate by
weather, day-part, city and distance bucket.
```sql
SELECT weather, COUNT(*) AS n,
       AVG(CASE WHEN is_late THEN 1.0 ELSE 0 END) AS late_rate
FROM orders WHERE status='delivered' GROUP BY weather ORDER BY late_rate DESC;
```

---

## Marketing

### Coupon effectiveness
Per campaign: redemptions, discount given, contribution margin, and
**margin returned per ₹ of discount** (`Σ margin ÷ Σ discount`). The core question:
*did this campaign create profit, or just orders?*

### CAC / ROAS
- **Blended CAC** = marketing spend ÷ new customers (per month).
- **ROAS** = net revenue ÷ spend.
- **CPI** = spend ÷ installs (by channel).

---

## Composite

### Product Health Index
Weighted 0–100 score across growth, retention, unit economics, experience and
operations — see [BUSINESS_ASSUMPTIONS.md](BUSINESS_ASSUMPTIONS.md#4-product-health-index).
