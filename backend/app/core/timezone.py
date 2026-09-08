"""Locale/timezone helper.

CLAUDE.md/NFR-007 fix the default timezone to Asia/Kolkata. "Today" must be
worked out in that timezone, not the server's local time or UTC - otherwise
a reading entered late at night in India could be attributed to the wrong
calendar day if the server happens to run in a different timezone (e.g. a
Hostinger VPS set to UTC).
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def today_local() -> date:
    return datetime.now(ZoneInfo(settings.timezone)).date()
