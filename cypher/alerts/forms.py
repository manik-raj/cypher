"""Parse and validate the alert create/edit form into DB-ready structures."""
from datetime import time

from ..exchanges import exchange_choices, get_adapter, normalize_pair

OPERATORS = [">", ">=", "<", "<=", "=="]
LEFT_METRICS = ["funding_fee", "difference"]
RIGHT_TYPES = ["constant", "exchange"]


def _valid_exchange(code: str) -> bool:
    try:
        get_adapter(code)
        return True
    except ValueError:
        return False


def _parse_time(value: str) -> time | None:
    try:
        hh, mm = value.split(":")[:2]
        return time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return None


def parse_alert_form(form) -> tuple[dict, list[dict], list[str]]:
    """Returns (fields, conditions, errors). fields maps to the alert columns."""
    errors: list[str] = []

    name = (form.get("name") or "").strip()
    alert_type = form.get("alert_type")
    exchange_primary = form.get("exchange_primary")
    exchange_secondary = (form.get("exchange_secondary") or "").strip() or None
    condition_logic = form.get("condition_logic", "AND")

    if not name:
        errors.append("Name is required.")
    if alert_type not in ("conditional", "scheduled"):
        errors.append("Invalid alert type.")
    if condition_logic not in ("AND", "OR"):
        condition_logic = "AND"

    trading_pair = None
    try:
        trading_pair = normalize_pair(form.get("trading_pair") or "")
    except ValueError as exc:
        errors.append(str(exc))

    if not exchange_primary or not _valid_exchange(exchange_primary):
        errors.append("A valid primary exchange is required.")
    if exchange_secondary and not _valid_exchange(exchange_secondary):
        errors.append("Secondary exchange is invalid.")
    if exchange_secondary and exchange_secondary == exchange_primary:
        errors.append("Primary and secondary exchanges must differ.")

    fields = {
        "name": name,
        "alert_type": alert_type,
        "trading_pair": trading_pair,
        "exchange_primary": exchange_primary,
        "exchange_secondary": exchange_secondary,
        "condition_logic": condition_logic,
        "check_interval_minutes": None,
        "schedule_kind": None,
        "daily_time_ist": None,
        "interval_hours": None,
    }

    conditions: list[dict] = []

    if alert_type == "conditional":
        try:
            interval = int(form.get("check_interval_minutes") or 0)
        except ValueError:
            interval = 0
        if interval <= 0:
            errors.append("Check frequency (minutes) must be a positive number.")
        fields["check_interval_minutes"] = interval or None
        conditions = _parse_conditions(form, exchange_secondary, errors)
        if not conditions and not any("condition" in e.lower() for e in errors):
            errors.append("A conditional alert needs at least one condition.")

    elif alert_type == "scheduled":
        schedule_kind = form.get("schedule_kind")
        if schedule_kind not in ("daily", "interval"):
            errors.append("Choose a schedule type (daily or interval).")
        fields["schedule_kind"] = schedule_kind
        if schedule_kind == "daily":
            t = _parse_time(form.get("daily_time_ist") or "")
            if t is None:
                errors.append("A valid daily time (HH:MM, IST) is required.")
            fields["daily_time_ist"] = t
        elif schedule_kind == "interval":
            try:
                hours = int(form.get("interval_hours") or 0)
            except ValueError:
                hours = 0
            if hours <= 0:
                errors.append("Interval (hours) must be a positive number.")
            fields["interval_hours"] = hours or None

    return fields, conditions, errors


def _parse_conditions(form, exchange_secondary, errors: list[str]) -> list[dict]:
    metrics = form.getlist("cond_left_metric")
    left_exchanges = form.getlist("cond_left_exchange")
    operators = form.getlist("cond_operator")
    right_types = form.getlist("cond_right_type")
    right_values = form.getlist("cond_right_value")
    right_exchanges = form.getlist("cond_right_exchange")

    conditions: list[dict] = []
    for i in range(len(metrics)):
        metric = metrics[i]
        if not metric:
            continue
        op = operators[i] if i < len(operators) else None
        rtype = right_types[i] if i < len(right_types) else None
        left_ex = left_exchanges[i] if i < len(left_exchanges) else None
        right_ex = right_exchanges[i] if i < len(right_exchanges) else None
        right_val_raw = right_values[i] if i < len(right_values) else None

        row_n = len(conditions) + 1
        if metric not in LEFT_METRICS:
            errors.append(f"Condition {row_n}: invalid left side.")
            continue
        if op not in OPERATORS:
            errors.append(f"Condition {row_n}: invalid operator.")
            continue

        cond = {
            "left_metric": metric,
            "left_exchange": None,
            "operator": op,
            "right_type": rtype,
            "right_value": None,
            "right_exchange": None,
        }

        if metric == "funding_fee":
            if not left_ex or not _valid_exchange(left_ex):
                errors.append(f"Condition {row_n}: choose a valid exchange for the funding fee.")
                continue
            cond["left_exchange"] = left_ex
        elif metric == "difference" and not exchange_secondary:
            errors.append(
                f"Condition {row_n}: 'difference' needs a secondary exchange set on the alert."
            )
            continue

        if rtype == "constant":
            try:
                cond["right_value"] = float(right_val_raw)
            except (TypeError, ValueError):
                errors.append(f"Condition {row_n}: enter a numeric value to compare against.")
                continue
        elif rtype == "exchange":
            if not right_ex or not _valid_exchange(right_ex):
                errors.append(f"Condition {row_n}: choose a valid exchange to compare against.")
                continue
            cond["right_exchange"] = right_ex
        else:
            errors.append(f"Condition {row_n}: invalid comparison target.")
            continue

        conditions.append(cond)

    return conditions


def form_context() -> dict:
    """Static choices for rendering the alert form."""
    return {
        "exchanges": exchange_choices(),
        "operators": OPERATORS,
        "left_metrics": LEFT_METRICS,
        "right_types": RIGHT_TYPES,
    }
