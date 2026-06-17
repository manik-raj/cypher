"""SQL for the app_setting key/value table."""
from .. import db


def get_all() -> dict[str, str]:
    rows = db.query("SELECT key, value FROM app_setting")
    return {r["key"]: r["value"] for r in rows}


def get(key: str, default=None):
    row = db.query_one("SELECT value FROM app_setting WHERE key = %s", (key,))
    return row["value"] if row else default


def upsert_many(values: dict[str, str]) -> None:
    if not values:
        return
    with db.get_conn() as conn, conn.cursor() as cur:
        for k, v in values.items():
            cur.execute(
                """
                INSERT INTO app_setting (key, value, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value, updated_at = now()
                """,
                (k, v),
            )
