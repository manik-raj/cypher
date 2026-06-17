"""Health/keep-alive endpoint, pinged by UptimeRobot to keep the Render
service awake so the in-process scheduler keeps running."""
from flask import Blueprint, jsonify

from . import db

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    db_ok = True
    detail = None
    try:
        db.query_one("SELECT 1 AS ok")
    except Exception as exc:  # pragma: no cover - reported, not raised
        db_ok = False
        detail = str(exc)
    status = "ok" if db_ok else "degraded"
    code = 200 if db_ok else 503
    return jsonify(status=status, database=db_ok, detail=detail), code
