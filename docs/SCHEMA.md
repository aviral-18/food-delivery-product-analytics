# Database Schema & ER Diagram

The schema follows a **star-ish** shape: `orders` is the central fact table
(analytical grain = one order) surrounded by dimension tables. Several derived
values (unit economics, time context, SLA flags) are **pre-computed onto
`orders`** at load time — mirroring how a real warehouse curates a `fct_orders`
model instead of recomputing on every query.

## ER diagram

```mermaid
erDiagram
    CITIES ||--o{ CUSTOMERS : "based in"
    CITIES ||--o{ RESTAURANTS : "located in"
    CITIES ||--o{ DELIVERY_PARTNERS : "operate in"
    CITIES ||--o{ ORDERS : "placed in"
    CITIES ||--o{ MARKETING_SPEND : "spend for"
    CITIES ||--o{ COUPONS : "scoped to"
    CUISINES ||--o{ RESTAURANTS : "primary cuisine"
    CUSTOMERS ||--o{ ORDERS : places
    RESTAURANTS ||--o{ ORDERS : fulfils
    DELIVERY_PARTNERS ||--o{ ORDERS : delivers
    COUPONS ||--o{ ORDERS : redeemed_on
    ORDERS ||--o{ ORDER_ITEMS : contains
    USERS ||--o{ AUDIT_LOGS : performs

    CITIES {
        int id PK
        string name
        string state
        string region
        int tier
        float population_millions
        date launch_date
    }
    CUISINES {
        int id PK
        string name
        string category
        numeric base_avg_price
    }
    CUSTOMERS {
        int id PK
        int city_id FK
        string email
        date signup_date
        string acquisition_channel
        string device
        bool is_active
        date churn_date
    }
    RESTAURANTS {
        int id PK
        int city_id FK
        int cuisine_id FK
        date onboarding_date
        int price_tier
        numeric commission_rate
        int base_prep_minutes
        numeric baseline_rating
    }
    DELIVERY_PARTNERS {
        int id PK
        int city_id FK
        string vehicle_type
        numeric reliability
        numeric baseline_rating
    }
    COUPONS {
        int id PK
        int city_id FK
        string code
        string campaign_name
        string discount_type
        numeric discount_value
        string target_segment
        numeric budget
    }
    MARKETING_SPEND {
        int id PK
        int city_id FK
        date month
        string channel
        numeric spend
        int installs
    }
    ORDERS {
        int id PK
        int customer_id FK
        int restaurant_id FK
        int city_id FK
        int delivery_partner_id FK
        int coupon_id FK
        datetime order_datetime
        date order_date
        string status
        bool is_first_order
        string day_part
        string weather
        numeric subtotal
        numeric discount_amount
        numeric net_revenue
        numeric contribution_margin
        int delivery_minutes
        bool is_late
        bool is_refunded
    }
    ORDER_ITEMS {
        int id PK
        int order_id FK
        string item_name
        int quantity
        numeric line_total
    }
    USERS {
        int id PK
        string email
        string role
        string hashed_password
    }
    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string entity
        datetime created_at
    }
```

## Tables

| Table | Grain | Purpose |
|-------|-------|---------|
| `cities` | one city | Geography dimension (tier, region, launch date) |
| `cuisines` | one cuisine | Catalog dimension |
| `customers` | one customer | Who orders — signup, channel, lifecycle |
| `restaurants` | one restaurant | Supply — cuisine, price tier, commission, prep time |
| `delivery_partners` | one rider | Last-mile supply, reliability |
| `coupons` | one campaign/code | Promotions with budget, targeting, scope |
| `marketing_spend` | city × month × channel | Paid acquisition spend for CAC/ROAS |
| `orders` | **one order (fact)** | The analytical core with pre-computed economics & SLA |
| `order_items` | one line item | Basket detail for drill-down |
| `users` | one operator | Platform login (Admin/PM/Analyst) |
| `audit_logs` | one action | Append-only privileged-action log |

## Key `orders` columns (pre-computed at load)

- **Economics:** `commission_amount`, `delivery_cost`, `payment_gateway_cost`,
  `support_cost`, `gross_revenue`, `net_revenue`, `contribution_margin`
- **Time context:** `order_date`, `day_part`, `is_weekend`, `is_festival`, `weather`
- **SLA:** `promised_minutes`, `prep_minutes`, `delivery_minutes`, `is_late`, `distance_km`
- **Lifecycle:** `is_first_order`
- **Experience:** `restaurant_rating`, `delivery_rating`, `is_refunded`, `refund_amount`

## Indexing

Composite indexes mirror the analytics engine's common `GROUP BY`s:
`(order_date, status)`, `(customer_id, order_date)`, `(city_id, order_date)`, plus
single-column indexes on every FK and the categorical filter columns.
