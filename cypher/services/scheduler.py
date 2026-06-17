"""In-process APScheduler. All triggers run in the configured timezone (IST),
so daily/interval jobs align to IST wall-clock time.

Jobs re-read the alert from the DB at run time, so edits/pauses take effect on
the next fire. Routes call sync_jobs() after any alert mutation to reconcile the
job set immediately.
"""
import atexit
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config import Config
from ..queries import alerts as alert_q
from . import alert_engine

log = logging.getLogger("cypher.scheduler")

_scheduler: BackgroundScheduler | None = None
_tz: ZoneInfo | None = None


def init(cfg: Config) -> None:
    global _scheduler, _tz
    if _scheduler is not None:
        return
    _tz = ZoneInfo(cfg.APP_TIMEZONE)
    _scheduler = BackgroundScheduler(timezone=_tz)
    _scheduler.start()
    atexit.register(lambda: _scheduler and _scheduler.shutdown(wait=False))
    sync_jobs()
    log.info("Scheduler started (tz=%s).", cfg.APP_TIMEZONE)


def is_running() -> bool:
    return _scheduler is not None and _scheduler.running


def _job_id(alert_id: int) -> str:
    return f"alert:{alert_id}"


def _trigger_for(alert: dict):
    if alert["alert_type"] == "conditional":
        minutes = alert.get("check_interval_minutes") or 60
        return IntervalTrigger(minutes=minutes, timezone=_tz)
    if alert.get("schedule_kind") == "daily":
        t = alert.get("daily_time_ist")
        if t is None:
            return None
        return CronTrigger(hour=t.hour, minute=t.minute, timezone=_tz)
    if alert.get("schedule_kind") == "interval":
        hours = alert.get("interval_hours") or 8
        return CronTrigger(hour=f"*/{hours}", minute=0, timezone=_tz)
    return None


def sync_jobs() -> None:
    """Reconcile scheduled jobs with the set of active alerts."""
    if not is_running():
        return

    active = alert_q.list_active("conditional") + alert_q.list_active("scheduled")
    wanted = {_job_id(a["id"]): a for a in active}

    for job in _scheduler.get_jobs():
        if job.id not in wanted:
            job.remove()

    for job_id, alert in wanted.items():
        trigger = _trigger_for(alert)
        if trigger is None:
            continue
        func = (
            alert_engine.run_conditional
            if alert["alert_type"] == "conditional"
            else alert_engine.run_scheduled
        )
        _scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            args=[alert["id"]],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
