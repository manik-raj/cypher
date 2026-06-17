"""Settings page: toggle and configure notification channels."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..services import notifier

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        values = {
            "telegram_enabled": "1" if request.form.get("telegram_enabled") else "0",
            "telegram_bot_token": request.form.get("telegram_bot_token", ""),
            "telegram_chat_id": request.form.get("telegram_chat_id", ""),
            "discord_enabled": "1" if request.form.get("discord_enabled") else "0",
            "discord_webhook_url": request.form.get("discord_webhook_url", ""),
        }
        notifier.save_settings(values)
        flash("Notification settings saved.", "success")
        return redirect(url_for("settings.index"))

    return render_template("settings/index.html", s=notifier.current_settings())


def init_app(app) -> None:
    app.register_blueprint(bp)
