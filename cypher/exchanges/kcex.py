"""Kcex exchange adapter.

Endpoint: GET https://www.kcex.com/fapi/v1/contract/ticker?symbol=ADA_USDT
Sample:   {"success":true,"code":0,"data":{...,"fundingRate":-0.000125,...,"timestamp":1781586026032}}
The ticker payload has no explicit next-collection time.

Kcex's WAF fingerprints the TLS handshake and 403s plain Python HTTP clients, so
requests go through the browser-impersonating helper in base.http_get_json.
"""
from .base import ExchangeAdapter, FundingRate, http_get_json

_URL = "https://www.kcex.com/fapi/v1/contract/ticker"


class KcexAdapter(ExchangeAdapter):
    code = "kcex"
    display_name = "Kcex"

    def to_symbol(self, pair: str) -> str:
        # Kcex uses uppercase with underscore: ADA_USDT
        return pair.upper()

    def fetch_funding(self, pair: str) -> FundingRate:
        symbol = self.to_symbol(pair)
        payload = http_get_json(_URL, params={"symbol": symbol})
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
