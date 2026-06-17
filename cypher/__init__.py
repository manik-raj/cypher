"""Cypher application factory."""
import logging

from flask import Flask

from . import db
from .config import Config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cypher")


def create_app(config: Config | None = None) -> Flask:
    cfg = config or Config()

    app = Flask(
        __name__,
        template_folder=cfg.TEMPLATES_DIR,
        static_folder=cfg.STATIC_DIR,
    )
    app.config.from_object(cfg)

    if cfg.DATABASE_URL:
        db.init_pool(cfg.DATABASE_URL)
        try:
            applied = db.run_migrations(cfg.MIGRATIONS_DIR)
            if applied:
                log.info("Applied migrations: %s", ", ".join(applied))
        except Exception:
            log.exception("Migration run failed; DB-backed features may be unavailable.")
    else:
        log.warning("DATABASE_URL not set; database features are disabled.")

    # Auth (also seeds the default admin once the schema exists).
    from . import auth

    auth.init_app(app)
    if cfg.DATABASE_URL:
        try:
            auth.ensure_default_admin(cfg)
        except Exception:
            log.exception("Could not ensure default admin user.")
        try:
            from .services import notifier

            notifier.seed_defaults(cfg)
        except Exception:
            log.exception("Could not seed notification settings.")

    # Blueprints
    from . import alerts, dashboard, settings
    from .health import bp as health_bp

    app.register_blueprint(health_bp)
    dashboard.init_app(app)
    alerts.init_app(app)
    settings.init_app(app)

    if cfg.SCHEDULER_ENABLED and cfg.DATABASE_URL:
        from .services import scheduler

        try:
            scheduler.init(cfg)
        except Exception:
            log.exception("Scheduler failed to start.")

    return app
