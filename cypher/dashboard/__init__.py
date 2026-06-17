"""Dashboard: overview of alerts and trackers."""
from flask import Blueprint, render_template
from flask_login import login_required

from ..alerts import present
from ..queries import alerts as alert_q

bp = Blueprint("dashboard", __name__)


@bp.get("/")
@login_required
def index():
    alerts = alert_q.list_alerts()
    conditions = alert_q.conditions_by_alert([a["id"] for a in alerts])

    view = []
    for a in alerts:
        conds = conditions.get(a["id"], [])
        view.append(
            {
                **a,
                "exchanges_text": present.exchanges_text(a),
                "schedule_text": present.schedule_text(a),
                "condition_texts": [present.condition_text(c) for c in conds],
            }
        )

    return render_template(
        "dashboard/index.html",
        alerts=view,
        history=alert_q.recent_history(limit=20),
        trackers=[],
    )


def init_app(app) -> None:
    app.register_blueprint(bp)
