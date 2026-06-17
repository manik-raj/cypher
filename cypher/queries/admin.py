"""SQL for the admin_user table."""
from .. import db


def count_admins() -> int:
    row = db.query_one("SELECT COUNT(*) AS n FROM admin_user")
    return row["n"] if row else 0


def get_by_id(admin_id: int) -> dict | None:
    return db.query_one("SELECT * FROM admin_user WHERE id = %s", (admin_id,))


def get_by_username(username: str) -> dict | None:
    return db.query_one("SELECT * FROM admin_user WHERE username = %s", (username,))


def create(username: str, password_hash: str) -> dict:
    return db.execute(
        """
        INSERT INTO admin_user (username, password_hash)
        VALUES (%s, %s)
        RETURNING id, username
        """,
        (username, password_hash),
        returning=True,
    )


def update_credentials(admin_id: int, username: str, password_hash: str) -> int:
    return db.execute(
        """
        UPDATE admin_user
           SET username = %s, password_hash = %s, updated_at = now()
         WHERE id = %s
        """,
        (username, password_hash, admin_id),
    )
