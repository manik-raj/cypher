"""Discord delivery channel (incoming webhook)."""
import logging

import requests

log = logging.getLogger("cypher.discord")
_TIMEOUT = 10
# Discord rejects messages over 2000 chars; alert messages are well under this.
_MAX_LEN = 1990


def send_message(text: str, webhook_url: str) -> tuple[bool, str | None]:
    """Returns (ok, error). Never raises."""
    if not webhook_url:
        return False, "Discord not configured (missing webhook URL)."

    content = text if len(text) <= _MAX_LEN else text[:_MAX_LEN] + "…"
    try:
        resp = requests.post(webhook_url, json={"content": content}, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        return False, f"Discord request failed: {exc}"

    # Webhooks return 204 No Content on success.
    if resp.status_code not in (200, 204):
        return False, f"Discord API {resp.status_code}: {resp.text[:200]}"
    return True, None
