# Food Delivery Product Analytics Platform

> An internal, enterprise-grade **Product Analytics platform** for a food-delivery
> marketplace — the kind of tool a Product Manager or Product Analyst at Eternal
> (Zomato), Swiggy, Uber Eats or DoorDash uses to answer business questions and
> make decisions.

This is **not** a chart gallery. Every page answers a business question:
*Why is retention decreasing? Which customer segments are most valuable? Are
coupons increasing revenue or destroying margin? Which cities deserve more
marketing spend? What's causing delivery delays?*

---

## ✨ What's inside

| Area | Highlights |
|------|-----------|
| **Executive Dashboard** | 14 KPI cards with period-over-period deltas, revenue trend, growth, and a weighted **Product Health Index** (0–100, graded A–F) |
| **Customer Analytics** | Acquisition **cohort retention matrix**, **RFM segmentation** (Champions → Hibernating), **CLV** (historical + predictive, by channel/city), repeat-purchase behaviour, order-frequency distribution, **journey funnel** |
| **Operations** | Delivery performance, **delay root-cause decomposition** (prep vs last-mile, by weather/city/distance), cancellation & refund analysis, peak-hour demand heatmap |
| **Catalog & Geography** | Restaurant performance & ranking, cuisine performance, **city performance with CAC/ROAS** |
| **Marketing** | **Coupon/campaign effectiveness** (margin returned per ₹ of discount), channel efficiency (blended CAC, ROAS, CPI) |
| **Forecasting** | Explainable trend + seasonality forecast with a confidence band |
| **AI Product Insights** | Deterministic, PM-language narratives per page: trends, anomalies, root-cause hypotheses, suggested A/B tests, risks & opportunities |
| **Product Decision Lab** 🧪 | A scenario simulator — *"cut coupons 20%, raise delivery fee ₹15"* → estimated impact on orders, GMV, net revenue, contribution margin & retention |
| **SQL Explorer** | The canonical SQL behind every metric, runnable against the live DB with timing, plus a guarded read-only ad-hoc query console |
| **Admin Panel** | User management, RBAC, audit logs, entity browsing, coupon controls |
| **Report Exports** | CSV · Excel · PDF for every tabular report |

---

## 🧱 Tech stack

**Backend** — FastAPI · SQLAlchemy 2.0 · PostgreSQL · Pandas · NumPy · Pydantic v2 · JWT (PyJWT + passlib/bcrypt)
**Frontend** — React · TypeScript · Vite · TailwindCSS · ShadCN-style UI · Recharts · TanStack Table/Query · React Router · Framer Motion
**Auth** — JWT access/refresh with role-based access control (Admin · Product Manager · Product Analyst)

---

## 📊 The dataset

A **generative** synthetic dataset — not random rows, but a per-customer *lifetime*
simulation (activation gate → monthly Poisson order rate → churn hazard) so that
retention, cohorts, CLV and RFM show **real, explainable structure**.

- **101,922 orders** · 223k order items · 30,000 customers · 2,000 restaurants · 100 delivery partners
- 16 Indian cities (tiers 1–3) · 16 cuisines · 24 months of history
- Seasonality, weekends, **13 festivals**, weather effects, marketing campaigns, restaurant onboarding, customer churn, delayed deliveries, cancellations and refunds
- Deliberately-encoded stories to discover — e.g. *rising paid-acquisition share erodes newer-cohort retention*, and *the aggressive coupon campaign drives orders but destroys margin*

Realism check (full run): AOV ≈ ₹400 · late-delivery ≈ 26% · cancellation ≈ 5% · refund ≈ 4% · repeat rate ≈ 70% · contribution margin ≈ 6–7% of GMV · blended CAC ≈ ₹380 · ROAS ≈ 1.0.

---

## 🚀 Quickstart

> Prerequisites: **Python 3.12+** and **PostgreSQL 14+**. See [docs/SETUP.md](docs/SETUP.md) for a full Windows walkthrough.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

copy .env.example .env            # then edit DATABASE_URL + SECRET_KEY

# create the database + generate & load 100k+ orders (~30–60s)
python -m app.data_generation.generate

# run the API
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** for interactive API docs.

**Default logins** (created by the seeder):

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@eternal.dev` | `admin123` |
| Product Manager | `pm@eternal.dev` | `pm123456` |
| Product Analyst | `analyst@eternal.dev` | `analyst123` |

```bash
# get a token
curl -X POST localhost:8000/api/v1/auth/login -H "Content-Type: application/json" \
     -d '{"email":"pm@eternal.dev","password":"pm123456"}'
```

---

## 📚 Documentation

- [docs/SETUP.md](docs/SETUP.md) — install PostgreSQL, configure, seed, run
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — clean architecture, folder structure & **interview talking points**
- [docs/SCHEMA.md](docs/SCHEMA.md) — ER diagram & table reference
- [docs/METRICS.md](docs/METRICS.md) — every metric: definition, formula & SQL
- [docs/BUSINESS_ASSUMPTIONS.md](docs/BUSINESS_ASSUMPTIONS.md) — unit economics, elasticities, data-generation model

---

## 🗺️ Project layout

```
Food Delivery Product Analytics/
├── backend/
│   ├── app/
│   │   ├── core/            # config, database, security, constants
│   │   ├── models/          # SQLAlchemy ORM (11 tables)
│   │   ├── data_generation/ # generative synthetic dataset
│   │   ├── analytics/       # the analytics engine (metrics, SQL, insights, decision lab)
│   │   ├── api/v1/          # FastAPI routers (auth + 12 analytics areas)
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # audit logging, cross-cutting services
│   │   └── main.py          # FastAPI app
│   └── requirements.txt
├── frontend/                # React SPA (in progress)
├── docs/
└── README.md
```

---

## ▶️ Running the frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173  (proxies /api to :8000)
```

The dev server proxies API calls to the FastAPI backend, so run the backend
first. Log in with any demo account above.

## 📈 Status

✅ **Backend complete & verified end-to-end** — data generator, analytics engine
(20+ analyses), JWT auth + RBAC, full REST API, decision lab, SQL explorer,
exports, admin panel.
✅ **Frontend complete** — 21 pages: Executive Dashboard, full Customer suite
(cohorts, RFM, CLV, repeat, frequency, funnel), Operations (delivery, delay
root-cause, cancellations, refunds, peak hours), Catalog/Geography (restaurants,
cuisines, cities), Marketing (coupons, channel efficiency), Forecasting, the
Product Decision Lab, SQL Explorer, and the Admin panel — with global filters,
AI insights panels, CSV/Excel/PDF export, dark/light themes, code-splitting, and
loading/empty/error states throughout.
