"""SQL for alerts, their conditions, and the send history."""
from .. import db

# Columns set directly from the alert form / engine.
_ALERT_COLS = (
    "name",
    "alert_type",
    "trading_pair",
    "exchange_primary",
    "exchange_secondary",
    "check_interval_minutes",
    "schedule_kind",
    "daily_time_ist",
    "interval_hours",
    "condition_logic",
)


def list_alerts() -> list[dict]:
    return db.query("SELECT * FROM alert ORDER BY created_at DESC")


def get_alert(alert_id: int) -> dict | None:
    return db.query_one("SELECT * FROM alert WHERE id = %s", (alert_id,))


def get_conditions(alert_id: int) -> list[dict]:
    return db.query(
        "SELECT * FROM alert_condition WHERE alert_id = %s ORDER BY position, id",
        (alert_id,),
    )


def conditions_by_alert(alert_ids: list[int]) -> dict[int, list[dict]]:
    """Bulk-fetch conditions for several alerts, grouped by alert_id."""
    if not alert_ids:
        return {}
    rows = db.query(
        "SELECT * FROM alert_condition WHERE alert_id = ANY(%s) ORDER BY position, id",
        (alert_ids,),
    )
    grouped: dict[int, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["alert_id"], []).append(r)
    return grouped


def _insert_conditions(cur, alert_id: int, conditions: list[dict]) -> None:
    for pos, c in enumerate(conditions):
        cur.execute(
            """
            INSERT INTO alert_condition
                (alert_id, left_metric, left_exchange, operator,
                 right_type, right_value, right_exchange, position)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                alert_id,
                c["left_metric"],
                c.get("left_exchange"),
                c["operator"],
                c["right_type"],
                c.get("right_value"),
                c.get("right_exchange"),
                pos,
            ),
        )


def create_alert(fields: dict, conditions: list[dict]) -> int:
    cols = ", ".join(_ALERT_COLS)
    placeholders = ", ".join(["%s"] * len(_ALERT_COLS))
    values = [fields.get(c) for c in _ALERT_COLS]
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO alert ({cols}) VALUES ({placeholders}) RETURNING id",
            values,
        )
        alert_id = cur.fetchone()["id"]
        _insert_conditions(cur, alert_id, conditions)
    return alert_id


def update_alert(alert_id: int, fields: dict, conditions: list[dict]) -> None:
    assignments = ", ".join(f"{c} = %s" for c in _ALERT_COLS)
    values = [fields.get(c) for c in _ALERT_COLS]
    values.append(alert_id)
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"UPDATE alert SET {assignments}, updated_at = now() WHERE id = %s",
            values,
        )
        cur.execute("DELETE FROM alert_condition WHERE alert_id = %s", (alert_id,))
        _insert_conditions(cur, alert_id, conditions)


def set_status(alert_id: int, status: str) -> int:
    return db.execute(
        "UPDATE alert SET status = %s, updated_at = now() WHERE id = %s",
        (status, alert_id),
    )


def delete_alert(alert_id: int) -> int:
    return db.execute("DELETE FROM alert WHERE id = %s", (alert_id,))


def list_active(alert_type: str) -> list[dict]:
    return db.query(
        "SELECT * FROM alert WHERE status = 'active' AND alert_type = %s ORDER BY id",
        (alert_type,),
    )


def mark_checked(alert_id: int, triggered: bool) -> None:
    if triggered:
        db.execute(
            "UPDATE alert SET last_checked_at = now(), last_triggered_at = now() WHERE id = %s",
            (alert_id,),
        )
    else:
        db.execute(
            "UPDATE alert SET last_checked_at = now() WHERE id = %s",
            (alert_id,),
        )


def record_history(
    alert_id: int, message_text: str, snapshot, delivery_status: str, error: str | None
) -> None:
    import json

    db.execute(
        """
        INSERT INTO alert_history (alert_id, message_text, snapshot, delivery_status, error)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (alert_id, message_text, json.dumps(snapshot), delivery_status, error),
    )


def recent_history(limit: int = 50) -> list[dict]:
    return db.query(
        """
        SELECT h.*, a.name AS alert_name
          FROM alert_history h
          JOIN alert a ON a.id = h.alert_id
         ORDER BY h.triggered_at DESC
         LIMIT %s
        """,
        (limit,),
    )
