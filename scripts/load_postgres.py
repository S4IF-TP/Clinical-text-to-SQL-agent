"""Load Synthea CSV output into PostgreSQL (drops and recreates the 8 tables).

Usage: uv run python scripts/load_postgres.py [--csv-dir data/synthea/csv]
Column types are inferred from the CSV header + a sample of values, so it survives
minor Synthea version differences. Runs as the admin user from .env.
"""

import argparse
import csv
import re
from pathlib import Path

import psycopg
from psycopg import sql

from csql.config import get_settings

TABLES = [
    "patients",
    "encounters",
    "conditions",
    "medications",
    "observations",
    "procedures",
    "allergies",
    "immunizations",
]

NUMERIC_COLUMNS = {
    "lat",
    "lon",
    "healthcare_expenses",
    "healthcare_coverage",
    "income",
    "base_encounter_cost",
    "total_claim_cost",
    "payer_coverage",
    "base_cost",
    "totalcost",
    "dispenses",
}

PRIMARY_KEYS = {"patients": "id", "encounters": "id"}

FOREIGN_KEYS = [
    ("encounters", "patient", "patients"),
    ("conditions", "patient", "patients"),
    ("conditions", "encounter", "encounters"),
    ("medications", "patient", "patients"),
    ("medications", "encounter", "encounters"),
    ("observations", "patient", "patients"),
    ("observations", "encounter", "encounters"),
    ("procedures", "patient", "patients"),
    ("procedures", "encounter", "encounters"),
    ("allergies", "patient", "patients"),
    ("allergies", "encounter", "encounters"),
    ("immunizations", "patient", "patients"),
    ("immunizations", "encounter", "encounters"),
]

INDEXES = [
    ("encounters", "patient"),
    ("encounters", "start"),
    ("encounters", "encounterclass"),
    ("conditions", "patient"),
    ("conditions", "description"),
    ("medications", "patient"),
    ("medications", "description"),
    ("observations", "patient"),
    ("observations", "description"),
    ("observations", "date"),
    ("procedures", "patient"),
    ("immunizations", "patient"),
    ("allergies", "patient"),
    ("observations", "category"),
    ("observations", "code"),
    ("conditions", "code"),
    ("conditions", "start"),
    ("medications", "start"),
    ("procedures", "description"),
    ("immunizations", "description"),
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def infer_type(name: str, samples: list[str]) -> str:
    if name in NUMERIC_COLUMNS:
        return "numeric"
    values = [v for v in samples if v != ""]
    if values and all(DATE_RE.match(v) for v in values):
        return "date"
    if values and all(TS_RE.match(v) for v in values):
        return "timestamp"
    return "text"


def load_table(conn: psycopg.Connection, csv_dir: Path, table: str) -> int:
    path = csv_dir / f"{table}.csv"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip().lower() for h in next(reader)]
        samples: list[list[str]] = [[] for _ in header]
        for i, row in enumerate(reader):
            if i >= 5000:
                break
            for j, v in enumerate(row):
                samples[j].append(v)

    types = [infer_type(h, s) for h, s in zip(header, samples, strict=True)]
    cols = sql.SQL(", ").join(
        sql.SQL("{} {}").format(sql.Identifier(h), sql.SQL(t))
        for h, t in zip(header, types, strict=True)
    )
    with conn.cursor() as cur:
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table)))
        cur.execute(sql.SQL("CREATE TABLE {} ({})").format(sql.Identifier(table), cols))
        copy_sql = sql.SQL("COPY {} FROM STDIN WITH (FORMAT csv, HEADER true)").format(
            sql.Identifier(table)
        )
        with path.open("rb") as f, cur.copy(copy_sql) as copy:
            while chunk := f.read(1 << 20):
                copy.write(chunk)
        cur.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
        return cur.fetchone()[0]


def add_constraints(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        for table, col in PRIMARY_KEYS.items():
            cur.execute(
                sql.SQL("ALTER TABLE {} ADD PRIMARY KEY ({})").format(
                    sql.Identifier(table), sql.Identifier(col)
                )
            )
        for table, col, ref in FOREIGN_KEYS:
            cur.execute(
                sql.SQL("ALTER TABLE {} ADD FOREIGN KEY ({}) REFERENCES {} (id)").format(
                    sql.Identifier(table), sql.Identifier(col), sql.Identifier(ref)
                )
            )
        for table, col in INDEXES:
            cur.execute(
                sql.SQL("CREATE INDEX {} ON {} ({})").format(
                    sql.Identifier(f"idx_{table}_{col}"), sql.Identifier(table), sql.Identifier(col)
                )
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", default="data/synthea/csv", type=Path)
    args = parser.parse_args()

    s = get_settings()
    with psycopg.connect(s.dsn(readonly=False), autocommit=False) as conn:
        for table in TABLES:
            n = load_table(conn, args.csv_dir, table)
            print(f"{table}: {n} rows")
        add_constraints(conn)
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(
                    sql.Identifier(s.readonly_user)
                )
            )
            cur.execute("ANALYZE")
        conn.commit()
    print("Done: constraints, indexes and read-only grants applied.")


if __name__ == "__main__":
    main()
