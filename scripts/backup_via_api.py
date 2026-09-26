"""Back up your WattLedger TN data from the production server, through its
public HTTPS API, into a local JSON file.

What it saves (everything the API shows for the account you log in with):
  - your account details (/auth/me - never the password)
  - every meter, and every reading for each meter
  - every meter reader visit (assessment), if the server is new enough
    to have that endpoint - skipped with a warning otherwise
  - all tariff plans, with their subsidy rules and slabs

What it can NOT save: other users' data, password hashes / security
answers, or anything the API doesn't expose. It is a data export, not a
full database dump - for that use `pg_dump` on the VPS (see README.md,
"Backups").

Usage (PowerShell, from the project folder):
    $env:WATTLEDGER_EMAIL = "you@example.com"
    uv run --project backend python scripts/backup_via_api.py
It asks for the password without showing it on screen. To run it
unattended, set $env:WATTLEDGER_PASSWORD first instead (never put the
password in this file or in Git).

Optional: $env:WATTLEDGER_API_URL to back up a different server
(default: the production API).

Only Python's standard library is used, so no extra packages are needed.
"""

import getpass
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_API_URL = "https://api.wattledger.aiwithbala.in"

# Backups go in <project>/backups/, which .gitignore excludes - they contain
# personal usage data and must never be committed.
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backup_via_api")


class ApiClient:
    """Tiny JSON-over-HTTPS helper that remembers the login token."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None

    def request(self, method: str, path: str, body: dict | None = None):
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    def get(self, path: str):
        return self.request("GET", path)


def read_credentials() -> tuple[str, str]:
    """Email/password from environment variables, or asked for on screen."""
    email = os.environ.get("WATTLEDGER_EMAIL") or input("WattLedger email: ").strip()
    password = os.environ.get("WATTLEDGER_PASSWORD")
    if not password:
        # getpass hides what you type, so the password never shows on screen.
        password = getpass.getpass("WattLedger password: ")
    if not email or not password:
        raise SystemExit("Email and password are required.")
    return email, password


def fetch_backup(client: ApiClient) -> dict:
    """Download everything the API exposes for the logged-in account."""
    me = client.get("/auth/me")
    meters = client.get("/meters")
    logger.info("Found %s meter(s).", len(meters))

    readings_by_meter = {}
    assessments_by_meter: dict | None = {}
    for meter in meters:
        meter_id = meter["id"]
        readings_by_meter[meter_id] = client.get(f"/meters/{meter_id}/readings")
        logger.info("Meter %s: %s reading(s).", meter["meter_number"], len(readings_by_meter[meter_id]))

        if assessments_by_meter is not None:
            try:
                assessments_by_meter[meter_id] = client.get(f"/meters/{meter_id}/assessments")
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
                # Server is older than the billing-history release.
                logger.warning("Server has no assessments endpoint yet - skipping meter reader visits.")
                assessments_by_meter = None

    tariffs = client.get("/tariffs")
    logger.info("Found %s tariff plan(s).", len(tariffs))

    return {
        "backup_format": 1,
        "source": client.base_url,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "user": me,
        "meters": meters,
        "readings_by_meter": readings_by_meter,
        "assessments_by_meter": assessments_by_meter,
        "tariff_plans": tariffs,
    }


def main() -> int:
    client = ApiClient(os.environ.get("WATTLEDGER_API_URL", DEFAULT_API_URL))
    logger.info("Backing up from %s", client.base_url)

    email, password = read_credentials()
    try:
        client.token = client.request("POST", "/auth/login", {"email": email, "password": password})["access_token"]
        backup = fetch_backup(client)
    except urllib.error.HTTPError as exc:
        logger.error("API call failed: HTTP %s %s", exc.code, exc.read().decode("utf-8", "replace"))
        return 1
    except urllib.error.URLError as exc:
        logger.error("Could not reach %s: %s", client.base_url, exc.reason)
        return 1

    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = BACKUP_DIR / f"wattledger-api-backup-{stamp}.json"
    # Write to a temporary name first, then rename, so an interrupted run
    # never leaves a half-written file that looks like a good backup.
    temp_file = out_file.with_suffix(".json.partial")
    temp_file.write_text(json.dumps(backup, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_file.replace(out_file)

    # Read it back to prove the file is complete, valid JSON.
    check = json.loads(out_file.read_text(encoding="utf-8"))
    total_readings = sum(len(r) for r in check["readings_by_meter"].values())
    logger.info(
        "Backup saved: %s (%s meters, %s readings, %s tariff plans).",
        out_file, len(check["meters"]), total_readings, len(check["tariff_plans"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
