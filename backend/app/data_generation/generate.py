"""
Dataset orchestrator.

`generate_dataset()` is pure (no DB) and returns every table as a list of dicts,
so it can be unit-tested and inspected offline. `persist()` writes the dataset to
any SQLAlchemy engine in dependency order using chunked bulk inserts.

Run end-to-end against the configured PostgreSQL database with:

    python -m app.data_generation.generate            # recreate + seed everything
    python -m app.data_generation.generate --keep     # keep existing schema
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import numpy as np
from dateutil.relativedelta import relativedelta
from faker import Faker
from sqlalchemy import Engine, insert

from app.core.config import settings
from app.core.constants import UserRole
from app.core.database import Base, engine as default_engine
from app.core.security import hash_password
from app.data_generation import entities as ent
from app.data_generation.orders import OrderSimulator
from app.models import (
    AuditLog, City, Coupon, Cuisine, Customer, DeliveryPartner,
    MarketingSpend, Order, OrderItem, Restaurant, User,
)

WINDOW_END = date(2026, 6, 30)


@dataclass
class Dataset:
    cities: list[dict] = field(default_factory=list)
    cuisines: list[dict] = field(default_factory=list)
    customers: list[dict] = field(default_factory=list)
    restaurants: list[dict] = field(default_factory=list)
    partners: list[dict] = field(default_factory=list)
    coupons: list[dict] = field(default_factory=list)
    marketing_spend: list[dict] = field(default_factory=list)
    orders: list[dict] = field(default_factory=list)
    order_items: list[dict] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        return {
            "cities": len(self.cities), "cuisines": len(self.cuisines),
            "customers": len(self.customers), "restaurants": len(self.restaurants),
            "partners": len(self.partners), "coupons": len(self.coupons),
            "marketing_spend": len(self.marketing_spend), "orders": len(self.orders),
            "order_items": len(self.order_items),
        }


_LATENT_PREFIX = "_"


def _strip_latent(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith(_LATENT_PREFIX)}


def generate_dataset(verbose: bool = True) -> Dataset:
    """Build the full dataset in memory (deterministic given settings.SEED)."""
    t0 = time.perf_counter()
    rng = np.random.default_rng(settings.SEED)
    faker = Faker("en_IN")
    Faker.seed(settings.SEED)

    window_start = WINDOW_END - relativedelta(months=settings.GEN_MONTHS) + relativedelta(days=1)

    def log(msg: str) -> None:
        if verbose:
            print(f"  [{time.perf_counter() - t0:6.1f}s] {msg}")

    log("building cities & cuisines...")
    cities = ent.build_cities(window_start)
    cuisines = ent.build_cuisines()

    log(f"building {settings.GEN_CUSTOMERS:,} customers...")
    customers = ent.build_customers(rng, faker, settings.GEN_CUSTOMERS, cities, window_start, WINDOW_END)

    log(f"building {settings.GEN_RESTAURANTS:,} restaurants...")
    restaurants = ent.build_restaurants(rng, faker, settings.GEN_RESTAURANTS, cities, cuisines, window_start, WINDOW_END)

    log(f"building {settings.GEN_PARTNERS:,} delivery partners...")
    partners = ent.build_partners(rng, faker, settings.GEN_PARTNERS, cities, window_start, WINDOW_END)

    log("building coupons & marketing spend...")
    coupons = ent.build_coupons(rng, cities, window_start, WINDOW_END)
    # Scale marketing budgets to the business size so CAC/ROAS stay realistic
    # regardless of the configured customer count (reference = 30k customers).
    customer_scale = settings.GEN_CUSTOMERS / 30_000
    marketing = ent.build_marketing_spend(rng, cities, window_start, WINDOW_END, customer_scale)

    log(f"simulating orders (target ~ {settings.GEN_ORDERS:,})...")
    sim = OrderSimulator(rng, cities, customers, restaurants, partners, coupons, cuisines, window_start, WINDOW_END)
    orders, order_items, lifecycle = sim.simulate()

    # Apply lifecycle (is_active / churn_date) back onto customers.
    for c in customers:
        upd = lifecycle.get(c["id"])
        if upd:
            c["is_active"] = upd["is_active"]
            c["churn_date"] = upd["churn_date"]

    ds = Dataset(
        cities=[_strip_latent(r) for r in cities],
        cuisines=[_strip_latent(r) for r in cuisines],
        customers=[_strip_latent(r) for r in customers],
        restaurants=[_strip_latent(r) for r in restaurants],
        partners=[_strip_latent(r) for r in partners],
        coupons=[_strip_latent(r) for r in coupons],
        marketing_spend=marketing,
        orders=orders,
        order_items=order_items,
    )
    log(f"done. {ds.summary()}")
    return ds


# --------------------------------------------------------------------------- #
#  Default operator accounts (analytics platform users)
# --------------------------------------------------------------------------- #
DEFAULT_USERS = [
    {"email": "admin@eternal.dev", "full_name": "Platform Admin", "role": UserRole.ADMIN, "password": "admin123"},
    {"email": "pm@eternal.dev", "full_name": "Priya PM", "role": UserRole.PRODUCT_MANAGER, "password": "pm123456"},
    {"email": "analyst@eternal.dev", "full_name": "Arjun Analyst", "role": UserRole.PRODUCT_ANALYST, "password": "analyst123"},
]


def _default_user_rows() -> list[dict]:
    return [
        {
            "email": u["email"], "full_name": u["full_name"], "role": str(u["role"]),
            "hashed_password": hash_password(u["password"]), "is_active": True,
        }
        for u in DEFAULT_USERS
    ]


# --------------------------------------------------------------------------- #
#  Persistence
# --------------------------------------------------------------------------- #
def _bulk_insert(engine: Engine, model, rows: list[dict], chunk: int = 5000) -> None:
    if not rows:
        return
    table = model.__table__
    with engine.begin() as conn:
        for i in range(0, len(rows), chunk):
            conn.execute(insert(table), rows[i : i + chunk])


def persist(ds: Dataset, engine: Engine = default_engine, recreate: bool = True, verbose: bool = True) -> None:
    """Write the dataset to the database in FK-dependency order."""
    if recreate:
        if verbose:
            print("  dropping & recreating schema...")
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    order = [
        (City, ds.cities), (Cuisine, ds.cuisines), (Customer, ds.customers),
        (Restaurant, ds.restaurants), (DeliveryPartner, ds.partners), (Coupon, ds.coupons),
        (MarketingSpend, ds.marketing_spend), (Order, ds.orders), (OrderItem, ds.order_items),
    ]
    for model, rows in order:
        t = time.perf_counter()
        _bulk_insert(engine, model, rows)
        if verbose:
            print(f"    inserted {len(rows):>7,} -> {model.__tablename__} ({time.perf_counter()-t:.1f}s)")

    _bulk_insert(engine, User, _default_user_rows())
    _bulk_insert(engine, AuditLog, [{
        "user_id": None, "action": "seed", "entity": "database",
        "detail": f"Seeded {ds.summary()}", "created_at": datetime.now(timezone.utc),
    }])
    if verbose:
        print("  seeded default users (admin/pm/analyst) + audit log.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate & load the analytics dataset.")
    parser.add_argument("--keep", action="store_true", help="Do not drop/recreate the schema.")
    args = parser.parse_args()

    print(f">> Generating dataset (seed={settings.SEED}) ...")
    ds = generate_dataset()
    print(">> Loading into database ...")
    persist(ds, recreate=not args.keep)
    print("[OK] Done.")


if __name__ == "__main__":
    main()
