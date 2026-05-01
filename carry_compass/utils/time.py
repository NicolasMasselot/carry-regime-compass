from datetime import date, datetime, timezone

import pandas as pd


def now_utc() -> datetime:
    """Return the current UTC timestamp.

    Returns:
        Timezone-aware datetime in UTC.
    """
    return datetime.now(timezone.utc)


def to_utc_naive(ts: date | datetime | pd.Timestamp | str) -> datetime:
    """Convert a date-like value to UTC-naive datetime.

    Args:
        ts: Date, datetime, pandas Timestamp or parseable date string.

    Returns:
        UTC-normalized datetime with timezone information stripped for storage.
    """
    timestamp = pd.Timestamp(ts)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(timezone.utc)
    else:
        timestamp = timestamp.tz_convert(timezone.utc)
    return timestamp.to_pydatetime().replace(tzinfo=None)


def business_days_between(start: date | datetime | str, end: date | datetime | str) -> int:
    """Count business days between two inclusive endpoints.

    Args:
        start: Start date-like value.
        end: End date-like value.

    Returns:
        Number of pandas business dates in the interval.
    """
    start_date = pd.Timestamp(start).date()
    end_date = pd.Timestamp(end).date()
    return len(pd.bdate_range(start_date, end_date))
