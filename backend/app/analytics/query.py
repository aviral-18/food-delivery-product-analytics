"""
Query execution helpers.

`run_query` executes a canonical SQL string against the session's engine,
applying the dialect shim and expanding IN-list parameters, and returns rows
plus timing and the *displayed* (Postgres canonical) SQL for the SQL Explorer.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.analytics.portable import adapt


def _cell(value: Any) -> Any:
    """Normalise a DB cell so PostgreSQL (Decimal) matches SQLite (float)."""
    if isinstance(value, Decimal):
        return float(value)
    return value


@dataclass
class QueryResult:
    rows: list[dict]
    columns: list[str]
    execution_ms: float
    sql: str                      # canonical PostgreSQL (for display)
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def scalar(self) -> Any:
        if self.rows and self.columns:
            return self.rows[0][self.columns[0]]
        return None

    def first(self) -> dict | None:
        return self.rows[0] if self.rows else None


def run_query(
    db: Session,
    sql: str,
    params: dict[str, Any] | None = None,
    expanding: Sequence[str] = (),
) -> QueryResult:
    """
    Execute `sql` (canonical Postgres) and return a QueryResult.

    `expanding` names the parameters that are IN-lists (bound with expanding
    bindparams so `col IN :ids` works portably).
    """
    params = params or {}
    dialect = db.get_bind().dialect.name
    exec_sql = adapt(sql, dialect)

    stmt = text(exec_sql)
    if expanding:
        stmt = stmt.bindparams(*[bindparam(name, expanding=True) for name in expanding])

    t0 = time.perf_counter()
    result = db.execute(stmt, params)
    columns = list(result.keys())
    rows = [{k: _cell(v) for k, v in r._mapping.items()} for r in result]
    elapsed = (time.perf_counter() - t0) * 1000.0

    return QueryResult(
        rows=rows,
        columns=columns,
        execution_ms=round(elapsed, 2),
        sql=sql.strip(),
        params=params,
    )
