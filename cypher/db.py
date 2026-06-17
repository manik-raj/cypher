"""Database access layer: psycopg3 connection pool, query helpers, and the
hand-written SQL migration runner. No ORM.

Always pass values as parameters (%s); never format them into the SQL string.
"""
import atexit
import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def init_pool(database_url: str) -> ConnectionPool:
    """Initialise the global connection pool (idempotent)."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=database_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        atexit.register(close_pool)
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised; set DATABASE_URL and call init_pool().")
    return _pool


def get_conn():
    """Context manager yielding a pooled connection. Commits on clean exit,
    rolls back on exception, then returns the connection to the pool."""
    return get_pool().connection()


def query(sql: str, params=None) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def query_one(sql: str, params=None) -> dict | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql: str, params=None, *, returning: bool = False):
    """Run an INSERT/UPDATE/DELETE. With returning=True, returns the single
    RETURNING row; otherwise returns the affected row count."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        if returning:
            return cur.fetchone()
        return cur.rowcount


def run_migrations(migrations_dir: str) -> list[str]:
    """Apply any *.sql files in migrations_dir not yet recorded in
    schema_migrations. Each file applies atomically with its version row.
    Returns the list of newly applied versions."""
    execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    applied = {r["version"] for r in query("SELECT version FROM schema_migrations")}

    newly: list[str] = []
    files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))
    for fname in files:
        version = fname.split("_", 1)[0]
        if version in applied:
            continue
        with open(os.path.join(migrations_dir, fname), "r", encoding="utf-8") as fh:
            sql = fh.read()
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql)
            cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        newly.append(version)
    return newly
