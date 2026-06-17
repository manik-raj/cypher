# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Phase 1 built and verified end-to-end against an Aiven Postgres dev DB: auth + admin seed,
exchange adapters (Antarctic live; Kcex geo-blocked from this host but code matches the
documented API), alerts CRUD (both types), the alert engine + Telegram notifier + IST-aligned
APScheduler, dashboard, and `/health`. Phase 2 (tracking history + Aster) is not built; its
DB tables already exist in `001_init.sql`. Requirements doc: `resources/project.pdf`.

## Commands

Use the venv interpreter only — never global Python. On Windows: `venv\Scripts\python.exe`.

```bash
venv\Scripts\python.exe -m pip install -r requirements.txt   # install deps
venv\Scripts\python.exe app.py                               # dev server (localhost:5000)
waitress-serve --listen=0.0.0.0:$PORT app:app                # production (Render) start command
```

Migrations run automatically on app startup (`db.run_migrations`); to run them standalone:
`venv\Scripts\python.exe -c "from cypher import db; from cypher.config import Config as C; db.init_pool(C().DATABASE_URL); print(db.run_migrations(C().MIGRATIONS_DIR))"`.
There is no test suite yet; verification has been done via `app.test_client()` one-off scripts.
Set `SCHEDULER_ENABLED=0` in such scripts to avoid starting the background scheduler thread.

## What Cypher is

A single Python web app that tracks crypto perpetual **funding rates** across multiple
exchanges and sends **Telegram alerts** based on user-configured conditions. Admins manage
alerts (and, in phase 2, trackers) through a browser dashboard. State lives in Postgres.
Deployed on Render.

Core requirement: **UI and backend are one process** (no separate API/worker split). Keep the
app deployable as a single Render service.

## Locked design decisions

- **Framework:** Flask + Jinja templates + Bootstrap. Flask-Login + hashed passwords for auth.
- **Database access:** **raw SQL via `psycopg` v3** with its connection pool — no ORM. SQL lives in
  a thin `db.py` (helpers: `query`, `query_one`, `execute`) plus per-feature query modules.
  Use parameterized queries (`%s`) only — never string-format values into SQL.
- **Migrations:** hand-written numbered `.sql` files in `migrations/` (`001_init.sql`, …), applied
  by a small runner that records applied versions in a `schema_migrations` table. No Alembic.
- **Scheduling:** in-process **APScheduler** with timezone `Asia/Kolkata`. All daily/interval/
  tracking jobs align to **IST wall-clock** (e.g. hourly = 1:00, 2:00 IST — not relative to when
  the job was created). Do not introduce a separate worker process for scheduling.
- **Keep-alive:** a public **`/health`** endpoint exists so UptimeRobot can ping the Render
  service and prevent free-tier sleeping (which would otherwise stop the scheduler).
- **Notifications:** pluggable channels (Discord, Telegram), each with an independent on/off
  toggle on the **Settings** page, persisted in `app_setting`. `services/notifier.py` fans a
  message out to every enabled channel; `services/discord.py` and `services/telegram.py` are the
  senders. Env vars only seed initial settings (default: Discord on, Telegram off). Messages are
  **plain text** so they render correctly on both channels. Adding a channel = a new sender
  module + wiring in `notifier.py` + a toggle in the Settings template.
- **Rate comparison:** compare the raw `fundingRate` exactly as each exchange API returns it.
  No cross-exchange normalization for differing funding intervals.
- **Difference convention:** `difference = exchange_primary − exchange_secondary`. The UI must
  make the direction explicit wherever a user picks the two exchanges.

## Architecture

### Exchange adapters (the extensibility seam)
Every exchange is one class implementing a common `ExchangeAdapter` interface, registered in a
code-level registry. **Adding an exchange = one new adapter file, no schema change.** Internal
trading pairs are normalized as `BASE_QUOTE` uppercase (e.g. `ADA_USDT`); each adapter translates
to its native symbol format.

Interface: `code`, `display_name`, `to_symbol(pair)`, `fetch_funding(pair) -> {funding_rate,
next_collection_time, raw}`.

| Exchange | Phase | Symbol format | Endpoint | Rate field |
|----------|-------|---------------|----------|------------|
| Antarctic | 1 | lowercase `ada_usdt` | `GET https://prod-gateway.antarctic.exchange/futures/fapi/market/v1/public/q/funding-rate?symbol=ada_usdt` | `data.fundingRate` |
| Kcex | 1 | uppercase `ADA_USDT` | `GET https://www.kcex.com/fapi/v1/contract/ticker?symbol=ADA_USDT` | `data.fundingRate` |
| Aster | 2 | TBD | TBD | TBD |

### Alerts (phase 1)
Two alert types share one `alert` table plus an `alert_condition` table (one alert may have
several conditions combined with AND/OR):

- **Conditional** — evaluated every `check_interval_minutes`; fires when its condition(s) hold.
  Conditions can be exchange-vs-constant (`ex1 funding fee > 0.04`) or exchange-vs-exchange
  (`kcex >= antarctic`), with operators `> >= < <= ==`. Left metric is either a single exchange's
  `funding_fee` or the `difference`.
- **Scheduled (time-based)** — sends at a daily IST time, or on a fixed interval (e.g. every 8h).

Every sent alert includes: alert type, trading pair, each exchange's funding fee, and the
difference (primary − secondary). Sends are recorded in `alert_history`.

**Percent semantics:** exchange APIs return a funding *rate* (e.g. `0.000748`). Cypher presents
and evaluates everything in **percent** — messages show `rate × 100` with a `%`, and conditions
are evaluated in percent space (fees/differences ×100; the entered constant is taken as a percent
as-is). So a threshold typed as `0.04` means 0.04%. See `_pct`/`_left_value`/`_right_value` in
`services/alert_engine.py`. Snapshots still store raw rates; `alert_condition.right_value` is
stored as the percent the user typed.

### Tracking (phase 2)
`tracker` + `funding_snapshot` tables store funding fees of all supported exchanges for a pair on
a chosen frequency, IST-aligned. Schema is included from the start so phase 2 needs no rework.

## Proposed layout

```
app.py                 # Flask app factory, blueprint registration, scheduler start
config.py              # env-driven config
cypher/
  auth/                # login, logout, change-password (verifies old password)
  dashboard/           # lists alerts + trackers
  alerts/              # CRUD + forms, both alert types
  tracking/            # phase 2
  exchanges/           # base.py (interface + registry), antarctic.py, kcex.py, aster.py
  services/            # alert_engine.py, telegram.py, scheduler.py
  db.py                # psycopg3 pool + query/execute helpers + migration runner
  queries/             # per-feature SQL query modules
  health.py            # /health for UptimeRobot
migrations/            # numbered .sql files
templates/  static/
```

## Environment / secrets (Render env vars)

- `DATABASE_URL` — Render Postgres connection string
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Default seeded admin: `admin` / `cypher-admin` (changeable in-app with the old password)

Keep an up-to-date `.env.example`. Commands (run, migrate, test) will be added to this file once
the corresponding tooling exists — do not invent commands before they work.
