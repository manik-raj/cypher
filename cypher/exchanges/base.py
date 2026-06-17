"""Exchange adapter interface and a small registry.

Adding a new exchange means writing one ExchangeAdapter subclass and registering
it in this package's __init__ — no database or schema changes required.

Trading pairs are normalised internally as ``BASE_QUOTE`` uppercase (e.g.
``ADA_USDT``); each adapter translates that to its own native symbol format.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from curl_cffi import requests as _http

# Some exchanges (e.g. Kcex) sit behind a WAF that fingerprints the TLS
# ClientHello (JA3) and 403s plain Python clients. curl_cffi impersonates a real
# browser's TLS/HTTP fingerprint so these requests look like a browser.
_IMPERSONATE = "chrome"
_TIMEOUT = 10


def http_get_json(url: str, params: dict | None = None, timeout: int = _TIMEOUT) -> dict:
    """GET a JSON endpoint with browser TLS impersonation. Raises on HTTP error."""
    resp = _http.get(url, params=params, impersonate=_IMPERSONATE, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


@dataclass
class FundingRate:
    exchange: str            # adapter code, e.g. "antarctic"
    pair: str                # normalised pair, e.g. "ADA_USDT"
    funding_rate: float      # raw rate as the exchange reports it
    next_collection_time: int | None  # epoch ms, if the API provides it
    raw: dict                # full decoded API payload


_PAIR_RE = re.compile(r"^[A-Z0-9]+_[A-Z0-9]+$")


def normalize_pair(pair: str) -> str:
    """Normalise user input like 'ada/usdt', 'ada-usdt', 'adausdt?' loosely to
    'ADA_USDT'. Raises ValueError if it can't be made into BASE_QUOTE form."""
    p = pair.strip().upper().replace("-", "_").replace("/", "_")
    if "_" not in p:
        raise ValueError(f"Pair '{pair}' must be in BASE_QUOTE form, e.g. ADA_USDT")
    if not _PAIR_RE.match(p):
        raise ValueError(f"Invalid trading pair: {pair!r}")
    return p


class ExchangeAdapter:
    code: str = ""
    display_name: str = ""
    # Known funding interval in hours if fixed for the venue, else None.
    funding_interval_hours: int | None = None

    def to_symbol(self, pair: str) -> str:
        raise NotImplementedError

    def fetch_funding(self, pair: str) -> FundingRate:
        raise NotImplementedError
