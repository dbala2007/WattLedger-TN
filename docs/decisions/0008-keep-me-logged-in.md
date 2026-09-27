# 0008 - "Keep me logged in" with per-device refresh tokens

**Status:** Decided (Phase 3 - authentication)

## Context

The app saved its single JWT access token and reused it on the next
start, but that token expires after 7 days (`ACCESS_TOKEN_EXPIRE_MINUTES`),
so users on Windows and Android were asked for their password again every
week. The user asked for an opt-in "always keep me logged in" option that
remembers the computer/phone.

Two options were considered:

1. **Just issue a very long-lived access token when ticked.** Simplest,
   but a JWT can't be cancelled before it expires: a lost phone would
   stay logged in for months, and the only way to stop it would be
   rotating `SECRET_KEY`, which logs out everyone.
2. **Per-device refresh tokens (chosen).** The anticipated
   `DeviceSession / RefreshToken` entity from CLAUDE.md section 10.
   Slightly more code, but each remembered device can be cancelled on its
   own.

## Decision

- `POST /auth/login` and `/auth/signup` accept optional `remember_me`
  and `device_name`. When `remember_me` is true the response also
  contains a `refresh_token`: 256 random bits (`secrets.token_urlsafe`).
- A `DeviceSession` row stores only the **SHA-256 hash** of that token
  (a fast hash is fine because the token is random, unlike a password),
  the device name, and `expires_at`.
- `POST /auth/refresh {refresh_token}` returns a new access token and
  pushes `expires_at` forward by `REMEMBER_ME_DAYS` (default 180) - a
  sliding window, so a device in regular use never expires.
- `POST /auth/logout {refresh_token}` revokes that one device.
  A password reset revokes **all** of the user's devices.
- The app (`AuthProvider`) saves both tokens in `flutter_secure_storage`
  only when the box is ticked. When unticked it saves nothing (and clears
  anything saved before), so closing the app logs the user out.
- `ApiClient` retries a request once after a 401 by renewing the access
  token through `AuthProvider` (a single shared renewal for concurrent
  requests; never for the refresh call itself). This covers both app
  start and an app left open in the background past 7 days.
- If the device is offline at startup, the saved tokens are kept (only a
  401 from the server deletes them).

## Consequences

- Existing app versions keep working unchanged: they don't send
  `remember_me`, so they get the old single-token behaviour.
- The refresh token is not rotated on each use (simpler; a stolen token
  could be used until the device logs out or the password is reset).
  Rotation can be added later without changing the table.
- On the web build the tokens live in browser storage, which a
  cross-site-scripting bug could read; acceptable for now since the web
  app renders no user-supplied HTML.
- No "list/sign out my devices" screen yet - the `device_name` and
  `last_used_at` columns are there for it.
