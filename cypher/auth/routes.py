"""Login, logout, and change-credentials routes."""
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from . import AdminUser
from ..queries import admin as admin_q

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        row = admin_q.get_by_username(username)
        if row and check_password_hash(row["password_hash"], password):
            login_user(AdminUser(row))
            return redirect(request.args.get("next") or url_for("dashboard.index"))
        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        row = admin_q.get_by_id(current_user.id)
        if not row or not check_password_hash(row["password_hash"], old_password):
            flash("Current password is incorrect.", "danger")
        elif not new_username:
            flash("Username cannot be empty.", "danger")
        elif len(new_password) < 6:
            flash("New password must be at least 6 characters.", "danger")
        elif new_password != confirm:
            flash("New password and confirmation do not match.", "danger")
        else:
            admin_q.update_credentials(
                current_user.id, new_username, generate_password_hash(new_password)
            )
            flash("Credentials updated successfully.", "success")
            return redirect(url_for("dashboard.index"))

    return render_template("auth/change_password.html", username=current_user.username)
