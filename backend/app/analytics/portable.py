"""
Dialect portability shim.

Canonical metric SQL is PostgreSQL. When the active connection is SQLite (used
for local dev / tests), we rewrite the small, well-defined set of Postgres
functions we rely on into SQLite equivalents. This keeps ONE canonical query per
metric (what the SQL Explorer displays) while letting the same logic run and be
verified without a Postgres server.

Supported rewrites: DATE_TRUNC('day'|'week'|'month'|'quarter'|'year', x),
EXTRACT(HOUR|DOW|MONTH|YEAR FROM x). Everything else in our SQL (CTEs, window
functions, SUM(CASE ...), COALESCE, NULLIF, standard joins) is valid on both.
"""
from __future__ import annotations

import re

_DATE_TRUNC_SQLITE = {
    "day": r"date(\1)",
    "week": r"date(\1, 'weekday 1', '-6 days')",  # ISO-ish: Monday start
    "month": r"date(\1, 'start of month')",
    "quarter": r"date(\1, 'start of month', '-' || ((CAST(strftime('%m', \1) AS INTEGER)-1) % 3) || ' months')",
    "year": r"date(\1, 'start of year')",
}

_EXTRACT_SQLITE = {
    "hour": r"CAST(strftime('%H', \1) AS INTEGER)",
    "dow": r"CAST(strftime('%w', \1) AS INTEGER)",
    "month": r"CAST(strftime('%m', \1) AS INTEGER)",
    "year": r"CAST(strftime('%Y', \1) AS INTEGER)",
    "day": r"CAST(strftime('%d', \1) AS INTEGER)",
}


def to_sqlite(sql: str) -> str:
    """Translate the Postgres-isms we use into SQLite-compatible SQL."""
    def _trunc(m: re.Match) -> str:
        unit = m.group(1).lower()
        expr = m.group(2).strip()
        template = _DATE_TRUNC_SQLITE.get(unit, r"date(\1)")
        return template.replace(r"\1", expr)

    def _extract(m: re.Match) -> str:
        field = m.group(1).lower()
        expr = m.group(2).strip()
        template = _EXTRACT_SQLITE.get(field, r"\1")
        return template.replace(r"\1", expr)

    # DATE_TRUNC('unit', expr)  — expr assumed paren-free (our columns are)
    sql = re.sub(
        r"DATE_TRUNC\(\s*'(\w+)'\s*,\s*([^,()]+?)\s*\)",
        _trunc, sql, flags=re.IGNORECASE,
    )
    # EXTRACT(FIELD FROM expr)
    sql = re.sub(
        r"EXTRACT\(\s*(\w+)\s+FROM\s+([^()]+?)\s*\)",
        _extract, sql, flags=re.IGNORECASE,
    )
    return sql


def adapt(sql: str, dialect_name: str) -> str:
    """Return SQL adapted to the given dialect ('postgresql' or 'sqlite')."""
    if dialect_name == "sqlite":
        return to_sqlite(sql)
    return sql
