# 0006 - Production deployment: Docker Compose + Caddy on the Hostinger VPS

**Status:** Decided (backend/website groundwork; desktop installer and
Play Store packaging tracked as follow-up)

## Context

The user asked how to move from local dev to a real deployment: the
website and backend on their existing Hostinger VPS and domain
(`aiwithbala.in`, with a `wattledger` subdomain), plus a real desktop
installer and a Play Store listing. This is CLAUDE.md's Phase 4
(PostgreSQL, Docker, a VPS, HTTPS) plus two further, largely independent
distribution steps that weren't part of the original phase plan.

## Decisions

**Reverse proxy: Caddy, not Nginx.** CLAUDE.md section 8 allows either.
Caddy issues and renews Let's Encrypt HTTPS certificates automatically
from a ~10-line config, with no separate certbot/cron setup - the
simplest option that's still production-suitable (CLAUDE.md working rule
7), which matters for a first deployment done by someone new to this.

**Two subdomains, not one domain with path-based routing**:
`wattledger.aiwithbala.in` (website) and `api.wattledger.aiwithbala.in`
(backend). The backend's routes (`/auth/login`, `/meters`, ...) aren't
prefixed with `/api`, so a single-domain path-based split would need
Caddy to rewrite paths before forwarding - two DNS A records to the same
IP is free and avoids that entirely.

**PostgreSQL driver: `psycopg` (v3) with the `[binary]` extra.** The
codebase already only touches the database through SQLModel/SQLAlchemy
and reads `DATABASE_URL` from settings (`app/db/session.py` was written
anticipating exactly this swap), so no query/model code needed to change -
only adding the driver dependency and making `CORS_ORIGINS` configurable
(previously hardcoded to `"*"`, which CLAUDE.md section 14 explicitly
flags as unfit for real deployment).

**The web app is built locally and uploaded, not built on the VPS.**
Building a Flutter web app needs the full Flutter SDK; installing that on
a VPS whose only other job is running two small Docker containers is a
heavier, slower footprint than running `flutter build web` once on the
dev machine (which already has the SDK) and `scp`-ing the ~few-MB static
output.

**Postgres and the backend are not published to the host** - only Caddy's
80/443 are. Both other containers are reachable solely over the private
Docker Compose network, so the database is never directly exposed to the
internet.

## Consequences

- No query/domain/service code changed for the Postgres migration - the
  existing test suite (94 tests) still runs unmodified against SQLite for
  fast local iteration; Postgres is only exercised for real on the VPS.
- Deploying a `master` change means: build+upload the web app, `git pull`,
  `docker compose up -d --build` on the VPS - documented as a runbook in
  README.md rather than a script, since there's no CI/CD pipeline yet and
  the user is doing this by hand for now.
- Desktop installer packaging (MSIX/Inno Setup) and Play Store submission
  (signing, store listing, privacy policy, Play Console account) are
  substantial, mostly-independent pieces of work not attempted in this
  round - both need `--dart-define=API_BASE_URL=https://api.wattledger.aiwithbala.in`
  baked in at build time once tackled.
- No automated database backups yet - `pg_dump` is documented as a manual
  command; CLAUDE.md's backup/restore requirement (Phase 2) still applies
  to the production database, not just local SQLite.
