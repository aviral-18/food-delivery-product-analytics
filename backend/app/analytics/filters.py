"""
Global analytics filters.

`Filters` renders a parameterized, AND-prefixed SQL fragment referencing the
standard aliases used across the engine: `o` (orders), `r` (restaurants),
`c` (customers). Metric queries that support filtering join `restaurants r`
and `customers c` so every filter condition is always valid, then splice in
`{filters}` after a `WHERE 1=1`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Dataset observation window (see data_generation.generate.WINDOW_END).
DATA_START = date(2024, 7, 1)
DATA_END = date(2026, 6, 30)


@dataclass
class Filters:
    start_date: str | None = None
    end_date: str | None = None
    city_ids: list[int] | None = None
    restaurant_ids: list[int] | None = None
    cuisine_ids: list[int] | None = None
    statuses: list[str] | None = None
    partner_ids: list[int] | None = None
    payment_methods: list[str] | None = None
    coupon_ids: list[int] | None = None
    channels: list[str] | None = None
    day_parts: list[str] | None = None
    is_weekend: bool | None = None
    is_festival: bool | None = None

    # ------------------------------------------------------------------ #
    def render(self, o: str = "o", r: str = "r", c: str = "c") -> tuple[str, dict, list[str]]:
        """Return (sql_fragment, params, expanding_param_names)."""
        conds: list[str] = []
        params: dict = {}
        expanding: list[str] = []

        if self.start_date:
            conds.append(f"{o}.order_date >= :f_start")
            params["f_start"] = self.start_date
        if self.end_date:
            conds.append(f"{o}.order_date <= :f_end")
            params["f_end"] = self.end_date

        def add_in(col: str, name: str, values: list) -> None:
            conds.append(f"{col} IN :{name}")
            params[name] = values
            expanding.append(name)

        if self.city_ids:
            add_in(f"{o}.city_id", "f_city", self.city_ids)
        if self.restaurant_ids:
            add_in(f"{o}.restaurant_id", "f_rest", self.restaurant_ids)
        if self.cuisine_ids:
            add_in(f"{r}.cuisine_id", "f_cuisine", self.cuisine_ids)
        if self.statuses:
            add_in(f"{o}.status", "f_status", self.statuses)
        if self.partner_ids:
            add_in(f"{o}.delivery_partner_id", "f_partner", self.partner_ids)
        if self.payment_methods:
            add_in(f"{o}.payment_method", "f_pay", self.payment_methods)
        if self.coupon_ids:
            add_in(f"{o}.coupon_id", "f_coupon", self.coupon_ids)
        if self.channels:
            add_in(f"{c}.acquisition_channel", "f_channel", self.channels)
        if self.day_parts:
            add_in(f"{o}.day_part", "f_daypart", self.day_parts)
        if self.is_weekend is not None:
            conds.append(f"{o}.is_weekend = :f_weekend")
            params["f_weekend"] = self.is_weekend
        if self.is_festival is not None:
            conds.append(f"{o}.is_festival = :f_festival")
            params["f_festival"] = self.is_festival

        clause = (" AND " + " AND ".join(conds)) if conds else ""
        return clause, params, expanding

    # ------------------------------------------------------------------ #
    @property
    def effective_start(self) -> str:
        return self.start_date or DATA_START.isoformat()

    @property
    def effective_end(self) -> str:
        return self.end_date or DATA_END.isoformat()

    def active_summary(self) -> dict:
        """Human-readable summary of which filters are active (for insights)."""
        out = {}
        for name in (
            "start_date", "end_date", "city_ids", "restaurant_ids", "cuisine_ids",
            "statuses", "partner_ids", "payment_methods", "coupon_ids", "channels",
            "day_parts", "is_weekend", "is_festival",
        ):
            val = getattr(self, name)
            if val not in (None, [], ""):
                out[name] = val
        return out
