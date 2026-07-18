# Setup Guide (Windows-first, works on macOS/Linux too)

This backend targets **PostgreSQL**. It also runs against SQLite with zero config
(handy for a quick look), because the ORM and the analytics engine are
dialect-portable — but PostgreSQL is the intended production database.

---

## 1. Prerequisites

- **Python 3.12+** — `python --version`
- **PostgreSQL 14+** — install from https://www.postgresql.org/download/windows/
  (during install, note the `postgres` superuser password you set)

Optional: [pgAdmin](https://www.pgadmin.org/) for a GUI.

---

## 2. Create the database

Using `psql` (added to PATH by the installer, e.g. `C:\Program Files\PostgreSQL\16\bin`):

```bash
psql -U postgres
```
```sql
CREATE DATABASE food_delivery_analytics;
-- optional dedicated user:
CREATE USER analytics WITH PASSWORD 'analytics';
GRANT ALL PRIVILEGES ON DATABASE food_delivery_analytics TO analytics;
\q
```

---

## 3. Configure the backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

```ini
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/food_delivery_analytics
SECRET_KEY=<paste a long random string>
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> **Want to run without installing PostgreSQL?** Set
> `DATABASE_URL=sqlite:///./analytics.db` instead. Everything works; it's just not
> the production target.

---

## 4. Generate & load the dataset

```bash
python -m app.data_generation.generate
```

This drops/recreates the schema, generates **100k+ orders across 24 months**, loads
them in dependency order, and seeds the three default users. Takes ~30–60s.

Flags:
- `--keep` — don't drop/recreate the schema (append into existing tables).

Tune volume via `.env` (`GEN_CUSTOMERS`, `GEN_RESTAURANTS`, `GEN_ORDERS`, …). The
generator is deterministic given `SEED`.

---

## 5. Run the API

```bash
uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

---

## 6. Smoke-test from the terminal

```bash
# login
curl -X POST localhost:8000/api/v1/auth/login -H "Content-Type: application/json" ^
     -d "{\"email\":\"pm@eternal.dev\",\"password\":\"pm123456\"}"

# use the returned access_token
curl localhost:8000/api/v1/executive/kpis -H "Authorization: Bearer <TOKEN>"
```

---

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| `password authentication failed` | Check `DATABASE_URL` credentials match your PostgreSQL user. |
| `could not connect to server` | PostgreSQL service isn't running — start it from Services or `pg_ctl`. |
| `ModuleNotFoundError: app` | Run commands from the `backend/` directory with the venv activated. |
| Console shows odd characters | Windows cp1252 console — set `set PYTHONIOENCODING=utf-8`. |
| bcrypt version warning | Harmless; `bcrypt==4.0.1` is pinned for passlib compatibility. |
