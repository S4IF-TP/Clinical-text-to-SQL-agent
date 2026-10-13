import psycopg

from csql.config import get_settings


def run_query(sql: str, max_rows: int | None = None) -> tuple[list[str], list[tuple]]:
    """Execute as the read-only role (read-only transaction, 5s statement_timeout)."""
    s = get_settings()
    limit = max_rows or s.max_rows
    with psycopg.connect(s.dsn(readonly=True)) as conn, conn.cursor() as cur:
        cur.execute(sql)
        columns = [d.name for d in cur.description] if cur.description else []
        rows = cur.fetchmany(limit)
    return columns, rows
