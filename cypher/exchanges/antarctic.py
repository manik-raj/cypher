"""Antarctic exchange adapter.

Endpoint: GET https://prod-gateway.antarctic.exchange/futures/fapi/market/v1/public/q/funding-rate?symbol=ada_usdt
Sample:   {"code":0,"msg":"success","data":{"symbol":"ada_usdt","fundingRate":"0.000748","nextCollectionTime":1781596800000},"bizCode":null}
"""
import requests

from .base import ExchangeAdapter, FundingRate

_URL = "https://prod-gateway.antarctic.exchange/futures/fapi/market/v1/public/q/funding-rate"
_TIMEOUT = 10


class AntarcticAdapter(ExchangeAdapter):
    code = "antarctic"
    display_name = "Antarctic"

    def to_symbol(self, pair: str) -> str:
        # Antarctic uses lowercase with underscore: ada_usdt
        return pair.lower()

    def fetch_funding(self, pair: str) -> FundingRate:
        symbol = self.to_symbol(pair)
        resp = requests.get(_URL, params={"symbol": symbol}, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") != 0:
            raise ValueError(f"Antarctic error for {symbol}: {payload.get('msg')}")
        data = payload.get("data") or {}
        if data.get("fundingRate") is None:
            raise ValueError(f"Antarctic: no funding rate for {symbol}")
        return FundingRate(
            exchange=self.code,
            pair=pair,
            funding_rate=float(data["fundingRate"]),
            next_collection_time=data.get("nextCollectionTime"),
            raw=payload,
        )
