"""
Database initialization.

Creates the full schema from the SQLAlchemy models (no data). Use this when you
want an empty, correctly-structured database — e.g. before running your own
seed, for tests, or for a fresh environment. For a fully populated analytics
database (100k+ orders + default users), run the generator instead:

    python -m app.data_generation.generate

Usage (from the `backend/` directory, with the venv active and DATABASE_URL set):

    python -m scripts.init_db                 # create tables if they don't exist
    python -m scripts.init_db --drop          # DROP existing tables, then recreate
    python -m scripts.init_db --with-users    # also seed the 3 default operator accounts

The target database must already exist (see docs/SETUP.md); this script creates
the tables inside it, it does not create the database itself.
"""
from __future__ import annotations

import argparse

from sqlalchemy import inspect

# Importing the models package registers every table on Base.metadata.
import app.models  # noqa: F401
from app.core.database import Base, engine
from app.data_generation.generate import _default_user_rows
from app.models import User


def init_db(drop: bool = False, with_users: bool = False) -> None:
    if drop:
        print("Dropping all tables ...")
        Base.metadata.drop_all(engine)

    print("Creating tables ...")
    Base.metadata.create_all(engine)

    tables = sorted(inspect(engine).get_table_names())
    print(f"  {len(tables)} tables ready: {', '.join(tables)}")

    if with_users:
        from sqlalchemy import insert

        with engine.begin() as conn:
            existing = conn.execute(User.__table__.select()).first()
            if existing is None:
                conn.execute(insert(User.__table__), _default_user_rows())
                print("  Seeded default users: admin@eternal.dev / pm@eternal.dev / analyst@eternal.dev")
            else:
                print("  Users already exist — skipping user seed.")

    print("[OK] Database initialized.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the database schema from the ORM models.")
    parser.add_argument("--drop", action="store_true", help="Drop existing tables before creating.")
    parser.add_argument("--with-users", action="store_true", help="Seed the default operator accounts.")
    args = parser.parse_args()
    init_db(drop=args.drop, with_users=args.with_users)


if __name__ == "__main__":
    main()
