"""Evaluate alerts against live funding rates, build messages, and deliver them.

Raw funding rates are compared exactly as each exchange returns them (no
cross-exchange normalization), per the project's locked decision.
"""
import logging
import operator

from ..alerts import present
from ..exchanges import get_adapter
from ..queries import alerts as alert_q
from . import notifier

log = logging.getLogger("cypher.engine")

_OPS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
}


def _exchanges_for(alert: dict, conditions: list[dict]) -> list[str]:
    """Ordered, de-duplicated list of exchange codes this alert needs."""
    ordered: list[str] = []

    def add(code):
        if code and code not in ordered:
            ordered.append(code)

    add(alert.get("exchange_primary"))
    add(alert.get("exchange_secondary"))
    for c in conditions:
        add(c.get("left_exchange"))
        add(c.get("right_exchange"))
    return ordered


def fetch_rates(codes: list[str], pair: str) -> tuple[dict, dict]:
    rates: dict[str, float] = {}
    errors: dict[str, str] = {}
    for code in codes:
        try:
            rates[code] = get_adapter(code).fetch_funding(pair).funding_rate
        except Exception as exc:  # network/geo/parse errors are reported, not raised
            errors[code] = str(exc)
            log.warning("Funding fetch failed for %s %s: %s", code, pair, exc)
    return rates, errors


def difference(alert: dict, rates: dict) -> float | None:
    p = rates.get(alert.get("exchange_primary"))
    s = rates.get(alert.get("exchange_secondary"))
    if p is None or s is None:
        return None
    return p - s


# Conditions are evaluated in PERCENT space: funding fees and differences are
# multiplied by 100, and the entered constant is taken as a percent as-is.
# (Exchange-vs-exchange comparisons are unaffected since both sides scale equally.)
def _left_value(alert, cond, rates):
    if cond["left_metric"] == "difference":
        d = difference(alert, rates)
        return None if d is None else d * 100
    r = rates.get(cond["left_exchange"])
    return None if r is None else r * 100


def _right_value(cond, rates):
    if cond["right_type"] == "constant":
        return None if cond["right_value"] is None else float(cond["right_value"])
    r = rates.get(cond["right_exchange"])
    return None if r is None else r * 100


def evaluate(alert: dict, conditions: list[dict], rates: dict) -> tuple[bool, list]:
    """Returns (triggered, per_condition_results). A result is True/False, or
    None when an operand could not be fetched."""
    results = []
    for c in conditions:
        left = _left_value(alert, c, rates)
        right = _right_value(c, rates)
        if left is None or right is None:
            results.append(None)
        else:
            results.append(_OPS[c["operator"]](left, right))

    if not conditions:
        triggered = False
    elif alert.get("condition_logic") == "OR":
        triggered = any(r is True for r in results)
    else:  # AND: every condition must be evaluable and true
        triggered = all(r is True for r in results)
    return triggered, results


def _pct(value) -> str:
    """Funding rate -> percentage string (API returns a rate, e.g. 0.000748 -> 0.0748%)."""
    return "N/A" if value is None else f"{value * 100:.4g}%"


def build_message(alert, conditions, rates, errors, results=None) -> str:
    lines = [
        f"🔔 {alert['name']} [{alert['alert_type']}]",
        f"Pair: {alert['trading_pair']}",
        "",
        "Funding fees:",
    ]
    for code in _exchanges_for(alert, conditions):
        note = f" (error: {errors[code]})" if code in errors and code not in rates else ""
        lines.append(f"  • {present.exchange_label(code)}: {_pct(rates.get(code))}{note}")

    if alert.get("exchange_secondary"):
        d = difference(alert, rates)
        lines.append(
            f"Difference ({present.exchange_label(alert['exchange_primary'])} − "
            f"{present.exchange_label(alert['exchange_secondary'])}): {_pct(d)}"
        )

    if conditions:
        lines.append("")
        lines.append(f"Conditions ({alert.get('condition_logic', 'AND')}):")
        results = results or [None] * len(conditions)
        for c, r in zip(conditions, results):
            mark = {True: "✅", False: "❌", None: "⚠️"}[r]
            lines.append(f"  {mark} {present.condition_text(c)}")

    return "\n".join(lines)


def _deliver(alert, message, snapshot):
    """Fan out to enabled channels; record one aggregated history row.
    Returns True if at least one enabled channel delivered."""
    results = notifier.send_alert(message)

    if not results:
        status, err = "failed", "No notification channel is enabled."
    else:
        oks = [ok for ok, _ in results.values()]
        failures = "; ".join(
            f"{ch}: {e}" for ch, (ok, e) in results.items() if not ok
        )
        if all(oks):
            status, err = "sent", None
        elif any(oks):
            status, err = "sent", f"partial — {failures}"
        else:
            status, err = "failed", failures

    snapshot = {**snapshot, "channels": {ch: ok for ch, (ok, _) in results.items()}}
    alert_q.record_history(alert["id"], message, snapshot, status, err)
    if status == "failed":
        log.warning("Alert %s delivery failed: %s", alert["id"], err)
    return status == "sent"


def run_conditional(alert_id: int) -> dict:
    """Returns {'triggered': bool, 'delivered': bool|None}."""
    alert = alert_q.get_alert(alert_id)
    if not alert or alert["status"] != "active" or alert["alert_type"] != "conditional":
        return {"triggered": False, "delivered": None}
    conditions = alert_q.get_conditions(alert_id)
    rates, errors = fetch_rates(_exchanges_for(alert, conditions), alert["trading_pair"])
    triggered, results = evaluate(alert, conditions, rates)

    delivered = None
    if triggered:
        message = build_message(alert, conditions, rates, errors, results)
        snapshot = {"rates": rates, "errors": errors, "difference": difference(alert, rates),
                    "triggered": True}
        delivered = _deliver(alert, message, snapshot)
    alert_q.mark_checked(alert_id, triggered)
    return {"triggered": triggered, "delivered": delivered}


def run_scheduled(alert_id: int) -> dict:
    """Returns {'delivered': bool}."""
    alert = alert_q.get_alert(alert_id)
    if not alert or alert["status"] != "active" or alert["alert_type"] != "scheduled":
        return {"delivered": None}
    rates, errors = fetch_rates(_exchanges_for(alert, []), alert["trading_pair"])
    message = build_message(alert, [], rates, errors)
    snapshot = {"rates": rates, "errors": errors, "difference": difference(alert, rates)}
    delivered = _deliver(alert, message, snapshot)
    alert_q.mark_checked(alert_id, True)
    return {"delivered": delivered}
