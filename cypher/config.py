"""Environment-driven configuration for Cypher."""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key")

    DATABASE_URL = os.environ.get("DATABASE_URL")

    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

    DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

    DEFAULT_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "cypher-admin")

    APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Kolkata")

    SCHEDULER_ENABLED = _bool(os.environ.get("SCHEDULER_ENABLED"), default=True)

    TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    MIGRATIONS_DIR = os.path.join(BASE_DIR, "migrations")
