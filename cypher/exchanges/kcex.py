"""Kcex exchange adapter.

Endpoint: GET https://www.kcex.com/fapi/v1/contract/ticker?symbol=ADA_USDT
Sample:   {"success":true,"code":0,"data":{...,"fundingRate":-0.000125,...,"timestamp":1781586026032}}
The ticker payload has no explicit next-collection time.
"""
import requests

from .base import ExchangeAdapter, FundingRate

_URL = "https://www.kcex.com/fapi/v1/contract/ticker"
_TIMEOUT = 10
# Kcex sits behind bot protection that 403s requests without a browser-like UA.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class KcexAdapter(ExchangeAdapter):
    code = "kcex"
    display_name = "Kcex"

    def to_symbol(self, pair: str) -> str:
        # Kcex uses uppercase with underscore: ADA_USDT
        return pair.upper()

    def fetch_funding(self, pair: str) -> FundingRate:
        symbol = self.to_symbol(pair)
        resp = requests.get(_URL, params={"symbol": symbol}, headers=_HEADERS, timeout=_TIMEOUT)
        if resp.status_code == 403 or "application/json" not in resp.headers.get("content-type", ""):
            raise ValueError(
                f"Kcex request blocked (HTTP {resp.status_code}); the API appears geo/IP "
                "restricted from this host. Verify reachability from the deployment region."
            )
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("success") or payload.get("code") != 0:
            raise ValueError(f"Kcex error for {symbol}: {payload!r}")
        data = payload.get("data") or {}
        if data.get("fundingRate") is None:
            raise ValueError(f"Kcex: no funding rate for {symbol}")
        return FundingRate(
            exchange=self.code,
            pair=pair,
            funding_rate=float(data["fundingRate"]),
            next_collection_time=None,
            raw=payload,
        )
