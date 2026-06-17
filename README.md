# Cypher

A web app that tracks crypto perpetual **funding rates** across exchanges and sends
**Telegram alerts** when user-defined conditions are met (or on a schedule). Admins manage
everything from a browser dashboard. UI, backend, and the scheduler run in **one** Python
process. State lives in Postgres.

- **Phase 1 (this build):** Antarctic + Kcex exchanges, conditional & time-based alerts,
  Telegram delivery, admin dashboard.
- **Phase 2 (planned):** funding-rate tracking/history storage, Aster exchange.

## Tech

Flask · psycopg 3 (raw SQL, no ORM) · APScheduler (IST-aligned) · Telegram Bot API ·
Bootstrap · deployed on Render.

## Local development

```bash
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt # macOS/Linux

cp .env.example .env        # then fill in DATABASE_URL and Telegram values
venv\Scripts\python.exe app.py
```

The app runs at http://localhost:5000. Migrations run automatically on startup, and a
default admin (`admin` / `cypher-admin`, overridable via env) is seeded on first run.
**Change the admin password after first login** (top-right username → change credentials).

## Configuration (env vars)

| Var | Purpose |
|-----|---------|
| `DATABASE_URL` | Postgres connection string (Aiven/Render); append `?sslmode=require` for Aiven |
| `SECRET_KEY` | Flask session signing key |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Seed values for the Telegram channel |
| `DISCORD_WEBHOOK_URL` | Seed value for the Discord channel |
| `DEFAULT_ADMIN_USERNAME` / `DEFAULT_ADMIN_PASSWORD` | Seeded on first run only |
| `APP_TIMEZONE` | Schedule timezone (default `Asia/Kolkata`) |
| `SCHEDULER_ENABLED` | `1` to run the in-process scheduler; `0` to disable |

### Notification channels
Alerts can be delivered to **Discord** and/or **Telegram**. Each channel has an independent
on/off switch on the **Settings** page (top nav), with values stored in the DB. Alerts go to
every channel that is switched on. The env vars above only seed the initial values on first
run — defaults are **Discord on, Telegram off**.

- **Discord:** create a channel webhook (Channel → Edit → Integrations → Webhooks) and paste
  the URL into Settings.
- **Telegram:** create a bot via [@BotFather](https://t.me/BotFather) for the **bot token**,
  message the bot / add it to a chat, then find the **chat id** (e.g. via
  `https://api.telegram.org/bot<token>/getUpdates`). Enter both in Settings and flip the switch.

Use **Run now** on any alert to test delivery to the enabled channels.

## Alerts

- **Conditional** — checked every N minutes; fires when its condition(s) hold. A condition
  compares a single exchange's funding fee, or the **difference = primary − secondary**,
  against a constant or another exchange (operators `> >= < <= ==`). Multiple conditions
  combine with AND/OR.
- **Scheduled** — sends at a daily IST time, or every N hours (IST-aligned).

Every alert message includes the alert type, trading pair, each exchange's funding fee, and
the difference (primary − secondary).

## Deployment (Render)

`render.yaml` defines a single web service:
- Build: `pip install -r requirements.txt`
- Start: `waitress-serve --listen=0.0.0.0:$PORT app:app`
- Health check: `/health`

Set `DATABASE_URL`, `TELEGRAM_*`, and `DEFAULT_ADMIN_PASSWORD` in the Render dashboard
(they are `sync: false`). Point **UptimeRobot** at `/health` to keep a free-tier instance
awake so the scheduler keeps running.

> **Kcex access note:** Kcex's API is geo/IP-restricted (returns 403 from some regions/hosts).
> Verify reachability from your Render region early; Antarctic is unaffected.
