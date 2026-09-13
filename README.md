# WattLedger TN

A Tamil Nadu household electricity and solar usage tracking application.

You enter daily cumulative EB (electricity board) and solar meter readings,
and the app automatically works out daily consumption, current billing-cycle
usage, and (in a later phase) an estimated Tamil Nadu domestic electricity
bill. See [`PRP.md`](PRP.md) for the full product requirements and
[`CLAUDE.md`](CLAUDE.md) for the architecture/working rules this project
follows.

## Status

**Phase 0-2 backend, plus a Flutter desktop/web/mobile-ready UI covering all 8 Phase 1 screens.** Implemented so far:

Frontend (Flutter, `frontend/`):
- Dashboard, Add/Edit Meter, Daily Reading Entry, Reading History,
  Billing Cycle Summary + Estimated Bill (combined), Tariff & Subsidy
  Settings, Settings screens (PRP.md section 11)
- Talks to the backend over HTTP; runs as a native Windows desktop app
  (`flutter run -d windows`) and in Chrome (web), same code both ways
- State managed with `provider`; models/services mirror the backend's
  schemas by hand (no code generation)

Phase 1 (reading MVP):
- Meter management (create/list/get)
- Daily reading entry with automatic EB/solar balance calculation
- Validation rules (duplicate date, decreasing readings, required solar
  field when solar tracking is enabled)
- Chronological recalculation on backdated inserts, edits, and deletes

Phase 2 (billing engine):
- Meter-specific billing-cycle window calculation (not tied to calendar
  months - PRP.md section 6). TNEB's bi-monthly cycle isn't a fixed
  interval - it's whenever the meter reader actually visits - so a
  meter's "last official assessment date" / "next expected assessment
  date" (Edit Meter screen) override the arithmetic entirely once set,
  and every calculation uses that real window (see
  `docs/decisions/0003-irregular-billing-cycles.md`)
- Effective-dated, editable tariff plans with subsidy rules and slabs
  (never hard-coded - PRP.md section 5)
- Bill estimate for the current cycle with a full slab-by-slab breakdown
- The backend auto-seeds a default tariff plan on startup whenever the
  database has none yet (`app/db/seed_data.py`) - it's never overwritten
  once a plan exists, so this only saves re-entering it after a dev
  database reset. Still not a verified TNERC/TNPDCL figure - see the
  warning in that file and PRP.md section 4

Phase 3 (auth, partial):
- Signup/login with hashed passwords (bcrypt) and JWT access tokens
- Every meter (and everything reached through it - readings, billing) is
  scoped to the logged-in user; tariff plans stay shared/unscoped
- Same login works identically on the Flutter web build and the Windows
  desktop build (`AuthProvider`/`flutter_secure_storage`), against the
  same backend and SQLite database
- Self-service password reset via two security questions chosen at
  signup (no email/SMTP setup yet, so this is the only reset path)
- Not yet done: email verification, multiple users per household,
  PostgreSQL, and real multi-device sync (still requires running the
  backend on one machine both clients can reach)

All of the above is covered by automated tests, including tariff boundary
tests, and exposed through a FastAPI HTTP API.

Not yet implemented: PostgreSQL/sync, Docker deployment, billing-assessment
history/official-bill comparison, backup/restore. See `PRP.md` section 7
for the full phase plan.

**Tariff data warning:** the seeded example tariff plan uses made-up slab
rates for development/testing - not verified TNERC/TNPDCL figures. See
PRP.md section 4's tariff-source policy before using this for a real bill.

## Repository layout

```text
wattledger-tn/
├── backend/            FastAPI + SQLModel backend (see backend/README.md)
├── frontend/           Flutter client (see frontend/README.md)
├── docs/                design decisions, tariff sources, API notes
├── .env.example         copy to backend/.env and fill in real values
└── PRP.md / CLAUDE.md   product requirements and working rules
```

## Backend quick start

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.13+.

```bash
cd backend
uv sync                                   # install dependencies
uv run pytest                             # run the automated tests
uv run uvicorn app.main:app --reload      # start the API locally
```

Then open http://127.0.0.1:8000/docs for interactive API documentation
(Swagger UI), generated automatically by FastAPI. (On a machine where port
8000 is already used by something else, pass `--port 8001` and update
`frontend/lib/core/app_config.dart` to match.)

A local `wattledger.db` SQLite file is created automatically on first run -
it is git-ignored, so each developer gets their own local data.

To try the billing engine, seed an example tariff plan first:

```bash
uv run python scripts/seed_dev_tariff.py
```

### Configuration

Copy `.env.example` to `backend/.env` and set `SECRET_KEY` to your own
random value (e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`)
before signing up any real account - it signs login tokens, and changing it
later logs everyone out. Everything else in `.env.example` has a workable
default for local development.

**Windows note:** Python's `zoneinfo` (used for the Asia/Kolkata timezone)
has no built-in timezone database on Windows - the `tzdata` package (a
dependency here) supplies it. Without it, any endpoint that needs "today's
date" raises `ZoneInfoNotFoundError`.

## Frontend quick start

Requires [Flutter](https://docs.flutter.dev/get-started/install) (this
project was built against 3.44.4, SDK at
`F:\flutter_windows_3.44.4-stable\flutter` on this machine, added to the
user PATH - restart your terminal if `flutter` isn't found) and, for the
Windows desktop target, Visual Studio Build Tools with the "Desktop
development with C++" workload (installed at `F:\VisualStudioBuildTools`
on this machine).

```bash
cd frontend
flutter pub get
flutter run -d windows    # native desktop app
flutter run -d chrome     # or in a browser
```

The backend must be running separately (see above) - the app calls
`http://127.0.0.1:8000` (`frontend/lib/core/app_config.dart`).

The app opens to a login/signup screen (Phase 3) - create an account on
first run. The login token is stored with `flutter_secure_storage`
(Windows Credential Manager on desktop, browser-side encrypted storage on
web), so you stay logged in between restarts on each platform.

**Rebuilding the Windows `.exe` needs one extra Visual Studio component**:
`flutter_secure_storage`'s Windows plugin needs the ATL headers, which
aren't part of a default "Desktop development with C++" install. In the
Visual Studio Installer, Modify → Individual components → check "C++ ATL
for latest v143 build tools (x86 & x64)".

## Architecture

Business rules (balance calculation, validation, recalculation) live in
`backend/app/domain/` and do not depend on the database or the web
framework, so they can be unit-tested directly and reused unchanged when
web/mobile clients are added later (CLAUDE.md section 8's "critical
architecture rule").

```text
API (FastAPI routes)
  -> Services (orchestration: fetch, validate, save)
    -> Domain (pure business rules - balance calc, validation)
    -> Repositories (database access via SQLModel)
```
