"""Exchange registry. Register adapters here; the rest of the app discovers
exchanges only through these functions."""
from .antarctic import AntarcticAdapter
from .base import ExchangeAdapter, FundingRate, normalize_pair
from .kcex import KcexAdapter

# code -> adapter instance. Order here is the display order in the UI.
_REGISTRY: dict[str, ExchangeAdapter] = {}


def _register(adapter: ExchangeAdapter) -> None:
    _REGISTRY[adapter.code] = adapter


_register(AntarcticAdapter())
_register(KcexAdapter())
# Phase 2: _register(AsterAdapter())


def get_adapter(code: str) -> ExchangeAdapter:
    try:
        return _REGISTRY[code]
    except KeyError:
        raise ValueError(f"Unknown exchange: {code!r}")


def all_adapters() -> list[ExchangeAdapter]:
    return list(_REGISTRY.values())


def exchange_choices() -> list[tuple[str, str]]:
    """(code, display_name) pairs for populating UI dropdowns."""
    return [(a.code, a.display_name) for a in _REGISTRY.values()]


__all__ = [
    "ExchangeAdapter",
    "FundingRate",
    "normalize_pair",
    "get_adapter",
    "all_adapters",
    "exchange_choices",
]
