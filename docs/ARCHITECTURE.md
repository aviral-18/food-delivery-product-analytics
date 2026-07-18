# Architecture & Interview Talking Points

## Layered (clean) architecture

```
 HTTP  ──►  api/v1 routers  ──►  analytics engine  ──►  SQL / ORM  ──►  PostgreSQL
                │                      │
             deps (auth,           services
             filters, RBAC)     (audit, exports)
```

Each layer has one job and depends only inward:

| Layer | Package | Responsibility |
|-------|---------|----------------|
| **Transport** | `app/api/v1/*`, `app/main.py` | HTTP routing, status codes, request/response models. No business logic. |
| **Dependencies** | `app/api/deps.py` | Auth resolution, RBAC guards, filter parsing. |
| **Analytics engine** | `app/analytics/*` | All metrics, SQL, insights, decision lab, SQL registry. **The core IP.** Pure functions of `(db, filters)`. |
| **Data access** | `app/analytics/query.py`, `app/models/*` | Query execution + dialect portability; ORM schema. |
| **Domain/config** | `app/core/*` | Settings, DB engine, security, constants. |
| **Data generation** | `app/data_generation/*` | The generative synthetic dataset (isolated; not on the request path). |

**Why it matters:** the engine functions take a `Session` and a `Filters` object
and return plain dicts. They are trivially unit-testable (they were developed
entirely against a SQLite fixture), reusable across HTTP endpoints, exports and
the SQL explorer, and free of any web-framework coupling.

---

## Notable design decisions

1. **Pre-computed fact table.** Unit economics and SLA flags are computed once at
   load time onto `orders`, not on every query — the warehouse pattern. Queries
   stay simple and fast, and the SQL Explorer reads cleanly.

2. **Dialect portability shim** (`analytics/portable.py`). Canonical metric SQL is
   PostgreSQL. A tiny translator rewrites the handful of Postgres-isms
   (`DATE_TRUNC`, `EXTRACT`) for SQLite, so the *exact same query logic* is
   testable locally without a database server while production stays PostgreSQL.

3. **SQL for aggregation, pandas for shape.** Heavy `GROUP BY` work runs in the
   database; matrix/segment transforms (cohort pivot, RFM quintiles, funnels,
   forecast) finish in pandas — the same division of labour a data team uses.

4. **Boundary serialization** (`analytics/util.to_native`). PostgreSQL returns
   `Decimal`, pandas returns `numpy` scalars — both break JSON. One recursive
   sanitizer at the API boundary normalises everything (and NaN → null).

5. **Explainable "AI" insights.** The insights engine is deterministic and
   rule-based: every sentence traces to a number. That's a feature, not a
   limitation — it's defensible and reproducible, which is what a real analytics
   surface needs.

6. **Generative data.** Retention/cohort/CLV structure *emerges* from a
   per-customer lifetime simulation, so the analytics discover real relationships
   instead of fitting noise.

---

## Security

- JWT **access + refresh** tokens (`app/core/security.py`), bcrypt-hashed passwords.
- **RBAC** via a `require_roles(...)` dependency factory: e.g. ad-hoc SQL execution
  is Analyst/Admin only; user management is Admin only.
- **Guarded SQL console** — single statement, `SELECT`/`WITH` only, mutation
  keywords blocked, auto-`LIMIT`.
- **Audit log** — logins, exports, SQL runs and admin actions are appended to
  `audit_logs` with actor, IP and detail.

---

## Interview talking points

**"Walk me through the business problem."**
> A food-delivery marketplace makes money on thin per-order margins, so PMs
> constantly trade off growth against unit economics: coupons drive orders but
> can destroy margin; fast delivery drives retention but costs fleet money. This
> platform quantifies those trade-offs so decisions are made on evidence.

**"How would you diagnose declining retention?"**
> Start at the cohort retention matrix — Month-1 retention drops from ~52% (early
> cohorts) to ~42% (recent). Segment by acquisition channel: paid-acquired and
> Tier-2 cohorts retain worse, and paid mix rose over the period. Cross-check CLV
> by channel (referral/organic > paid). Hypothesis: we scaled paid acquisition and
> cut first-order incentives, importing lower-intent users. Test: a second-order
> nudge for paid first-time buyers.

**"Are coupons working?"**
> Look at margin returned per ₹ of discount, not redemptions. The aggressive %
> campaign has high volume but near-zero/negative margin per ₹; a modest flat
> campaign returns far more. Recommendation: cap or retire the inefficient one and
> raise minimum order values — quantified in the Decision Lab.

**"What's causing delivery delays?"**
> Decompose delivery time: prep is ~55% of it, so the lever is kitchens, not
> riders. Weather is the shock (storm 90%+ late vs clear ~17%). Late orders refund
> at ~2× the on-time rate — a direct experience-to-cost link. Fixes: dynamic ETAs
> in bad weather, kitchen auto-accept/batching, and targeting the worst cities.

**"How is the health score built?"**
> A weighted composite across growth, retention, unit economics, experience and
> operations, each normalised to a documented target band. It's a conversation
> starter that points to the weakest pillar — not a black box.

**"How would you productionise this?"**
> Alembic migrations, a read replica for analytics, materialised views or a dbt
> layer for the heaviest aggregations, Redis caching on the filter-keyed metric
> responses, and moving the insights rules toward a config-driven rules engine.
