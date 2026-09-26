"""Bring the local SQLite database up to date from a production API backup
made by scripts/backup_via_api.py.

For the backup's user (matched by email in the local database):
  - Meters are matched by meter number. A meter that only exists in the
    backup is created locally with the same settings. Settings of meters
    that already exist locally are NOT changed - differences are reported.
  - Readings missing locally are added; readings whose EB/solar units
    differ are corrected to the backup's values. Everything goes through
    the normal reading service, so balances are recalculated exactly as
    the app would and the usual validation rules apply.
  - Meter reader visits (assessments) in the backup that are missing
    locally are added (older backups have none - that's fine).
  - Nothing is ever deleted. Local-only readings are listed in the report.

Safety:
  - Default is a DRY RUN: the import runs against a temporary copy of the
    database and only the report is shown. Nothing real changes.
  - With --apply, the real database is first backed up (SQLite online
    backup) to backend/wattledger.db.pre-api-import-<timestamp>-backup.

Usage (from the project folder):
    uv run --project backend python scripts/import_api_backup.py backups/<file>.json
    uv run --project backend python scripts/import_api_backup.py backups/<file>.json --apply
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
LOCAL_DB = BACKEND_DIR / "wattledger.db"


def _dec(value) -> Decimal | None:
    """The API sends decimals as strings ("1786.400") - keep them exact."""
    return None if value is None else Decimal(str(value))


def _sqlite_backup(source: Path, target: Path) -> None:
    """Consistent copy even while the backend has the file open."""
    src, dst = sqlite3.connect(source), sqlite3.connect(target)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("backup_file", type=Path, help="JSON file written by backup_via_api.py")
    parser.add_argument("--apply", action="store_true", help="change the real local database (default: dry run)")
    args = parser.parse_args()

    backup = json.loads(args.backup_file.resolve().read_text(encoding="utf-8"))

    # Pick which database file the app code will open BEFORE importing it -
    # app.db.session creates its engine from DATABASE_URL at import time.
    if args.apply:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safety_copy = BACKEND_DIR / f"wattledger.db.pre-api-import-{stamp}-backup"
        _sqlite_backup(LOCAL_DB, safety_copy)
        target_db = LOCAL_DB
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="wattledger-dryrun-"))
        target_db = temp_dir / "dryrun.db"
        _sqlite_backup(LOCAL_DB, target_db)
    os.environ["DATABASE_URL"] = f"sqlite:///{target_db.as_posix()}"

    # The app reads backend/.env relative to the working directory.
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, str(BACKEND_DIR))

    from sqlmodel import Session, select  # noqa: E402

    from app.core.logging import get_logger  # noqa: E402
    from app.db.session import create_db_and_tables, engine  # noqa: E402
    from app.domain.readings import ReadingValidationError  # noqa: E402
    from app.models.enums import SolarMode  # noqa: E402
    from app.models.meter import Meter  # noqa: E402
    from app.repositories import billing_assessment_repository, reading_repository, user_repository  # noqa: E402
    from app.services import billing_assessment_service, meter_service, reading_service  # noqa: E402

    logger = get_logger("import_api_backup")
    logger.info("Mode: %s", "APPLY to real database" if args.apply else "DRY RUN on a temporary copy")
    if args.apply:
        logger.info("Safety backup of local database written to %s", safety_copy)

    create_db_and_tables()
    problems: list[str] = []

    with Session(engine) as session:
        email = backup["user"]["email"]
        user = user_repository.get_by_email(session, email)
        if user is None:
            logger.error("No local account for %s - sign up locally first, then re-run.", email)
            return 1

        local_meters = {m.meter_number: m for m in session.exec(select(Meter).where(Meter.user_id == user.id))}

        for remote_meter in backup["meters"]:
            number = remote_meter["meter_number"]
            meter = local_meters.get(number)

            if meter is None:
                meter = meter_service.create_meter(
                    session,
                    user_id=user.id,
                    meter_number=number,
                    display_name=remote_meter["display_name"],
                    solar_mode=SolarMode(remote_meter["solar_mode"]),
                    billing_cycle_reference_date=date.fromisoformat(remote_meter["billing_cycle_reference_date"])
                    if remote_meter["billing_cycle_reference_date"] else None,
                    cycle_length_months=remote_meter["cycle_length_months"],
                )
                logger.info("Meter %s: created locally.", number)
            else:
                for field in ("display_name", "solar_mode", "billing_cycle_reference_date", "cycle_length_months",
                              "last_assessment_date", "next_expected_assessment_date", "active"):
                    local_value = getattr(meter, field)
                    local_value = local_value.isoformat() if isinstance(local_value, date) else (
                        local_value.value if hasattr(local_value, "value") else local_value)
                    if local_value != remote_meter[field]:
                        logger.info("Meter %s: setting %s differs (local=%s, server=%s) - left unchanged.",
                                    number, field, local_value, remote_meter[field])

            # --- Readings, oldest first so each one validates against the
            # correct previous reading.
            remote_readings = sorted(backup["readings_by_meter"].get(remote_meter["id"], []),
                                     key=lambda r: r["reading_date"])
            local_by_date = {r.reading_date: r for r in reading_repository.list_for_meter(session, meter.id)}
            added = corrected = unchanged = 0

            for remote in remote_readings:
                reading_date = date.fromisoformat(remote["reading_date"])
                eb, solar = _dec(remote["eb_units"]), _dec(remote["solar_units"])
                local = local_by_date.pop(reading_date, None)
                try:
                    if local is None:
                        reading_service.create_reading(
                            session, meter_id=meter.id, user_id=user.id, reading_date=reading_date,
                            eb_units=eb, solar_units=solar, notes=remote["notes"],
                        )
                        added += 1
                    elif local.eb_units != eb or local.solar_units != solar:
                        logger.info("Meter %s %s: correcting eb %s->%s, solar %s->%s",
                                    number, reading_date, local.eb_units, eb, local.solar_units, solar)
                        reading_service.update_reading(
                            session, local.id, user.id, eb_units=eb, solar_units=solar, notes=remote["notes"],
                        )
                        corrected += 1
                    else:
                        unchanged += 1
                except ReadingValidationError as exc:
                    session.rollback()
                    problems.append(f"Meter {number} {reading_date}: not imported - {exc.errors}")

            logger.info("Meter %s: %s added, %s corrected, %s already identical.", number, added, corrected, unchanged)
            for local_only in sorted(local_by_date):
                logger.info("Meter %s %s: exists only locally - kept.", number, local_only)

            # --- Meter reader visits (only in backups from newer servers).
            remote_visits = (backup.get("assessments_by_meter") or {}).get(remote_meter["id"], [])
            for visit in remote_visits:
                assessed_on = date.fromisoformat(visit["assessed_on"])
                if billing_assessment_repository.get_by_meter_and_date(session, meter.id, assessed_on) is None:
                    billing_assessment_service.create_assessment(
                        session, meter_id=meter.id, user_id=user.id, assessed_on=assessed_on,
                        official_bill_amount=_dec(visit["official_bill_amount"]), notes=visit["notes"],
                    )
                    logger.info("Meter %s: added meter reader visit on %s.", number, assessed_on)

        for number in sorted(set(local_meters) - {m["meter_number"] for m in backup["meters"]}):
            logger.info("Meter %s exists only locally - kept.", number)

    for problem in problems:
        logger.warning(problem)

    engine.dispose()  # release the file so the dry-run copy can be removed
    if not args.apply:
        shutil.rmtree(target_db.parent, ignore_errors=True)
        logger.info("Dry run finished - nothing was changed. Re-run with --apply to import.")
    else:
        logger.info("Import finished.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
