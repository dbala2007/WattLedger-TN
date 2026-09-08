"""Regression test for a real bug found during manual testing: on Windows,
Python's zoneinfo module has no timezone database unless the `tzdata`
package is installed, so ZoneInfo("Asia/Kolkata") raised
ZoneInfoNotFoundError. This just needs to not raise.
"""

from datetime import date

from app.core.timezone import today_local


def test_today_local_does_not_raise():
    result = today_local()
    assert isinstance(result, date)
