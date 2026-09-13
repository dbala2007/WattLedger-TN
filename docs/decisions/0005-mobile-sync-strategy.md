# 0005 - Mobile app sync: no separate sync protocol, same backend

**Status:** Decided (Android enabled; iOS and remote/internet access deferred)

## Context

CLAUDE.md section 1 requires the architecture support "shared synchronized
data across all clients" and a mobile release without rewriting business
logic. With the backend, auth, and per-user data scoping already in place
(Phase 3), the question was what "sync" actually means for a first mobile
build, and how much of that to build now versus later.

## Decision

**No sync protocol is built at all.** Every client - Windows, web, and now
Android - is a thin HTTP client of the same FastAPI backend and reads/writes
the same database. There is no local database on any client, no offline
cache, and therefore no merge/conflict logic needed: opening the app always
shows the live server state. This was already true for Windows/web; Android
just needed to be able to reach the same backend.

Scope chosen for this round (the user picked "same Wi-Fi only" over also
standing up remote/internet access):

- The backend binds to `0.0.0.0` instead of `127.0.0.1` so devices other
  than this PC can reach it on the local network.
- `AppConfig.apiBaseUrl` is now `String.fromEnvironment('API_BASE_URL', ...)`
  instead of a hardcoded literal, defaulting to `127.0.0.1:8001` (correct
  for Windows/web, which run on the same machine as the backend) and
  overridden with `--dart-define=API_BASE_URL=http://<LAN-IP>:8001` when
  running on a phone, which is a separate device on the network.
- `android/app/build.gradle.kts`'s `compileSdk` was bumped to 37 -
  `flutter_secure_storage` (already used for the login token on
  Windows/web) requires it, one version above this Flutter release's own
  default.
- iOS was not enabled - it requires a Mac/Xcode, which this (Windows)
  development machine doesn't have.

Explicitly **not** done in this round: PostgreSQL migration, Docker,
a VPS, or HTTPS (CLAUDE.md Phase 4) - all of which would be needed for the
phone to reach the backend from anywhere other than this Wi-Fi network
(mobile data, a different location). That's a separate, larger decision
involving real hosting costs and setup, deferred until asked for.

## Consequences

- Any authenticated client immediately sees any other client's changes on
  next load/refresh - "sync" reduces to "don't cache, always ask the
  server," which was already the design.
- Testing the phone build requires it to be on the same Wi-Fi as whichever
  machine is running the backend, and that machine's LAN IP can change
  (DHCP) - documented in README.md rather than hardcoded anywhere.
- Moving to real remote access later (Phase 4) doesn't require touching
  this sync model - only where `API_BASE_URL` points and how the backend
  is hosted.
