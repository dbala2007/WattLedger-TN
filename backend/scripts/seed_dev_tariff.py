"""Manually seed the local dev database with the default tariff plan, if it
doesn't already have one. Normally unnecessary - the backend does this
itself on startup (see app.db.seed_data, called from app/main.py's
lifespan) - this script exists for seeding a database without starting the
whole server, e.g. right after wiping wattledger.db during development.

IMPORTANT: This is the household's own entered tariff figures, not a
verified TNERC/TNPDCL order - see app/db/seed_data.py's docstring and
PRP.md section 4's tariff-source policy before trusting it for a real bill.

Run with (from the backend/ folder):
    uv run python scripts/seed_dev_tariff.py
"""

import sys
from pathlib import Path

# Running this file directly (not as a -m module) only puts scripts/ itself
# on sys.path, not backend/ - so "import app...." would fail without this.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.db.seed_data import seed_default_tariff_plan_if_missing
from app.db.session import create_db_and_tables, engine

if __name__ == "__main__":
    create_db_and_tables()
    with Session(engine) as session:
        seed_default_tariff_plan_if_missing(session)
    print("Done (no-op if a tariff plan already existed).")
