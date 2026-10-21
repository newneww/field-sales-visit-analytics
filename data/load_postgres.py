"""Create the raw schema and load data/output/*.csv into PostgreSQL.

Works with any PostgreSQL: a local one or a hosted one such as Neon.

Usage:
    export DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"
    python data/load_postgres.py
"""
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = ROOT / "sql" / "01_schema.sql"
CSV_DIR = ROOT / "data" / "output"

# Parents before children, so foreign keys are satisfied.
TABLES = [
    "territories", "reps", "agents", "stores", "skus",
    "visit_plans", "visits", "order_lines", "agent_stock",
]


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Set DATABASE_URL first (see the docstring at the top of this file).")

    with psycopg.connect(url) as conn:
        conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        with conn.cursor() as cur:
            # reps.manager_id points at reps itself; ASMs come first in the CSV.
            for table in TABLES:
                path = CSV_DIR / f"{table}.csv"
                with path.open("rb") as f, cur.copy(
                    f"COPY raw.{table} FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')"
                ) as copy:
                    while chunk := f.read(1 << 16):
                        copy.write(chunk)
                cur.execute(f"SELECT count(*) FROM raw.{table}")
                print(f"raw.{table:<12} {cur.fetchone()[0]:>7,} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
