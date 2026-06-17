"""Authentication: Flask-Login wiring, the admin user model, and admin seeding."""
import logging

from flask import redirect, url_for
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash

from ..config import Config
from ..queries import admin as admin_q

log = logging.getLogger("cypher.auth")

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."


class AdminUser(UserMixin):
    def __init__(self, row: dict):
        self.id = row["id"]
        self.username = row["username"]
        self.password_hash = row["password_hash"]


@login_manager.user_loader
def load_user(user_id: str):
    row = admin_q.get_by_id(int(user_id))
    return AdminUser(row) if row else None


@login_manager.unauthorized_handler
def _unauthorized():
    return redirect(url_for("auth.login"))


def ensure_default_admin(cfg: Config) -> None:
    """Seed the default admin account on first run (when none exists)."""
    if admin_q.count_admins() == 0:
        admin_q.create(
            cfg.DEFAULT_ADMIN_USERNAME,
            generate_password_hash(cfg.DEFAULT_ADMIN_PASSWORD),
        )
        log.info("Seeded default admin user '%s'.", cfg.DEFAULT_ADMIN_USERNAME)


def init_app(app) -> None:
    login_manager.init_app(app)
    from .routes import bp

    app.register_blueprint(bp)
