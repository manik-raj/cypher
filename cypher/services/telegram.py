"""Telegram delivery channel. Sends plain text (no markup) for portability."""
import logging

import requests

log = logging.getLogger("cypher.telegram")
_TIMEOUT = 10


def send_message(text: str, token: str, chat_id: str) -> tuple[bool, str | None]:
    """Returns (ok, error). Never raises."""
    if not token or not chat_id:
        return False, "Telegram not configured (missing bot token or chat id)."

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url, json={"chat_id": chat_id, "text": text}, timeout=_TIMEOUT
        )
    except requests.RequestException as exc:
        return False, f"Telegram request failed: {exc}"

    if resp.status_code != 200:
        return False, f"Telegram API {resp.status_code}: {resp.text[:200]}"
    return True, None
