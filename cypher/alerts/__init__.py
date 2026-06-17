"""Alerts feature: CRUD routes for both alert types."""
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from ..queries import alerts as alert_q
from ..services import alert_engine, scheduler
from .forms import form_context, parse_alert_form

bp = Blueprint("alerts", __name__, url_prefix="/alerts")


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        fields, conditions, errors = parse_alert_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "alerts/form.html",
                mode="new",
                alert=request.form,
                conditions=conditions,
                **form_context(),
            )
        alert_id = alert_q.create_alert(fields, conditions)
        scheduler.sync_jobs()
        flash("Alert created.", "success")
        return redirect(url_for("dashboard.index", _anchor=f"alert-{alert_id}"))

    return render_template(
        "alerts/form.html", mode="new", alert={}, conditions=[], **form_context()
    )


@bp.route("/<int:alert_id>/edit", methods=["GET", "POST"])
@login_required
def edit(alert_id: int):
    alert = alert_q.get_alert(alert_id)
    if not alert:
        flash("Alert not found.", "warning")
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        fields, conditions, errors = parse_alert_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "alerts/form.html",
                mode="edit",
                alert={**alert, **request.form.to_dict()},
                conditions=conditions,
                **form_context(),
            )
        alert_q.update_alert(alert_id, fields, conditions)
        scheduler.sync_jobs()
        flash("Alert updated.", "success")
        return redirect(url_for("dashboard.index", _anchor=f"alert-{alert_id}"))

    return render_template(
        "alerts/form.html",
        mode="edit",
        alert=alert,
        conditions=alert_q.get_conditions(alert_id),
        **form_context(),
    )


@bp.post("/<int:alert_id>/pause")
@login_required
def pause(alert_id: int):
    alert_q.set_status(alert_id, "paused")
    scheduler.sync_jobs()
    flash("Alert paused.", "info")
    return redirect(url_for("dashboard.index"))


@bp.post("/<int:alert_id>/resume")
@login_required
def resume(alert_id: int):
    alert_q.set_status(alert_id, "active")
    scheduler.sync_jobs()
    flash("Alert resumed.", "success")
    return redirect(url_for("dashboard.index"))


@bp.post("/<int:alert_id>/delete")
@login_required
def delete(alert_id: int):
    alert_q.delete_alert(alert_id)
    scheduler.sync_jobs()
    flash("Alert deleted.", "info")
    return redirect(url_for("dashboard.index"))


@bp.post("/<int:alert_id>/run")
@login_required
def run_now(alert_id: int):
    alert = alert_q.get_alert(alert_id)
    if not alert:
        flash("Alert not found.", "warning")
        return redirect(url_for("dashboard.index"))

    if alert["alert_type"] == "conditional":
        res = alert_engine.run_conditional(alert_id)
        if res["triggered"] and res["delivered"]:
            flash("Condition met — alert sent to enabled channels.", "success")
        elif res["triggered"] and res["delivered"] is False:
            flash("Condition met, but delivery failed (check Settings).", "danger")
        else:
            flash("Checked now — condition not met, no alert sent.", "info")
    else:
        res = alert_engine.run_scheduled(alert_id)
        if res["delivered"]:
            flash("Alert sent to enabled channels.", "success")
        else:
            flash("Delivery failed (check Settings — is a channel enabled?).", "danger")
    return redirect(url_for("dashboard.index"))


def init_app(app) -> None:
    app.register_blueprint(bp)
