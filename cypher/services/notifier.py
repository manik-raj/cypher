"""Notification settings + multi-channel dispatch.

Channels (Telegram, Discord) are toggled independently from the Settings UI; the
values live in the app_setting table. send_alert() fans a message out to every
enabled, configured channel.
"""
import logging

from ..config import Config
from ..queries import settings as settings_q
from . import discord, telegram

log = logging.getLogger("cypher.notifier")

# Keys persisted in app_setting and editable from the Settings page.
SETTING_KEYS = (
    "telegram_enabled",
    "telegram_bot_token",
    "telegram_chat_id",
    "discord_enabled",
    "discord_webhook_url",
)


def _get_bool(values: dict, key: str) -> bool:
    return values.get(key) == "1"


def current_settings() -> dict:
    return settings_q.get_all()


def save_settings(form_values: dict) -> None:
    clean = {k: (form_values.get(k) or "").strip() for k in SETTING_KEYS}
    settings_q.upsert_many(clean)


def seed_defaults(cfg: Config) -> None:
    """On first run, default Telegram OFF and Discord ON, seeding any creds from env."""
    existing = settings_q.get_all()
    defaults = {
        "telegram_enabled": "0",
        "telegram_bot_token": cfg.TELEGRAM_BOT_TOKEN or "",
        "telegram_chat_id": cfg.TELEGRAM_CHAT_ID or "",
        "discord_enabled": "1",
        "discord_webhook_url": cfg.DISCORD_WEBHOOK_URL or "",
    }
    missing = {k: v for k, v in defaults.items() if k not in existing}
    if missing:
        settings_q.upsert_many(missing)
        log.info("Seeded notification settings: %s", ", ".join(missing))


def channel_status() -> list[dict]:
    """For UI summaries: which channels are enabled and configured."""
    s = settings_q.get_all()
    return [
        {
            "name": "Telegram",
            "enabled": _get_bool(s, "telegram_enabled"),
            "configured": bool(s.get("telegram_bot_token") and s.get("telegram_chat_id")),
        },
        {
            "name": "Discord",
            "enabled": _get_bool(s, "discord_enabled"),
            "configured": bool(s.get("discord_webhook_url")),
        },
    ]


def send_alert(text: str) -> dict[str, tuple[bool, str | None]]:
    """Send to every enabled channel. Returns {channel: (ok, error)} for enabled
    channels only (empty dict if none are enabled)."""
    s = settings_q.get_all()
    results: dict[str, tuple[bool, str | None]] = {}

    if _get_bool(s, "telegram_enabled"):
        results["telegram"] = telegram.send_message(
            text, s.get("telegram_bot_token", ""), s.get("telegram_chat_id", "")
        )
    if _get_bool(s, "discord_enabled"):
        results["discord"] = discord.send_message(text, s.get("discord_webhook_url", ""))

    return results
