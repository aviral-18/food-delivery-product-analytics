"""
Analytics engine.

The single source of truth for every business metric. Queries are written as
canonical **PostgreSQL** and executed directly. A thin portability shim rewrites
the handful of Postgres-isms (DATE_TRUNC, EXTRACT) when the bound engine is
SQLite, so the exact same query logic is unit-testable locally while remaining
production PostgreSQL. Complex matrix shaping (cohorts, RFM, funnels, forecast)
fetches aggregated rows via SQL and finishes the transformation in pandas.
"""
