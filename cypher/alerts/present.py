"""Human-readable summaries of alerts and conditions for the UI and messages."""
from ..exchanges import get_adapter


def exchange_label(code: str | None) -> str:
    if not code:
        return "—"
    try:
        return get_adapter(code).display_name
    except ValueError:
        return code


def condition_text(cond: dict) -> str:
    if cond["left_metric"] == "difference":
        left = "difference (primary − secondary)"
    else:
        left = f"{exchange_label(cond['left_exchange'])} funding fee"

    if cond["right_type"] == "constant":
        right = f"{_fmt_num(cond['right_value'])}%"
    else:
        right = f"{exchange_label(cond['right_exchange'])} funding fee"

    return f"{left} {cond['operator']} {right}"


def schedule_text(alert: dict) -> str:
    if alert["alert_type"] == "conditional":
        n = alert.get("check_interval_minutes")
        return f"every {n} min" if n else "—"
    if alert.get("schedule_kind") == "daily":
        t = alert.get("daily_time_ist")
        return f"daily at {t.strftime('%H:%M') if hasattr(t, 'strftime') else t} IST"
    if alert.get("schedule_kind") == "interval":
        return f"every {alert.get('interval_hours')}h IST"
    return "—"


def exchanges_text(alert: dict) -> str:
    primary = exchange_label(alert.get("exchange_primary"))
    secondary = alert.get("exchange_secondary")
    if secondary:
        return f"{primary} vs {exchange_label(secondary)}"
    return primary


def _fmt_num(value) -> str:
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)
