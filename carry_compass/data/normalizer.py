import pandas as pd

CANONICAL_COLS = ["open", "high", "low", "close", "adj_close", "volume"]


def _empty_frame() -> pd.DataFrame:
    empty = pd.DataFrame(columns=CANONICAL_COLS)
    empty.index = pd.DatetimeIndex([], name="date")
    return empty


def normalize_yf_frame(df: pd.DataFrame | None, ticker: str) -> pd.DataFrame:
    """Normalize raw ``yf.download`` output into the project OHLCV schema.

    Args:
        df: Raw yfinance frame, possibly empty or MultiIndex-columned.
        ticker: Requested Yahoo ticker, used to select MultiIndex columns.

    Returns:
        Date-indexed frame with canonical lowercase OHLCV columns and no timezone.
    """
    if df is None or df.empty:
        return _empty_frame()

    normalized = df.copy()
    if isinstance(normalized.columns, pd.MultiIndex):
        try:
            normalized = normalized.xs(ticker, axis=1, level=-1)
        except KeyError:
            normalized.columns = normalized.columns.get_level_values(0)

    normalized.columns = [str(column).lower().replace(" ", "_") for column in normalized.columns]
    if "adj_close" not in normalized.columns and "close" in normalized.columns:
        normalized["adj_close"] = normalized["close"]

    index = pd.to_datetime(normalized.index)
    if index.tz is not None:
        index = index.tz_convert("UTC").tz_localize(None)
    normalized.index = index.normalize()
    normalized.index.name = "date"

    normalized = normalized[~normalized.index.duplicated(keep="last")]
    normalized = normalized.reindex(columns=CANONICAL_COLS)
    normalized = normalized.dropna(subset=["close"])
    return normalized


def detect_gaps(df: pd.DataFrame, max_gap_bdays: int = 5) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Detect long missing-business-day stretches in a price frame.

    Args:
        df: Canonical price frame indexed by date.
        max_gap_bdays: Minimum gap length, in business days, to report.

    Returns:
        List of inclusive ``(start, end)`` missing-date ranges.
    """
    if df.empty:
        return []

    index = pd.DatetimeIndex(pd.to_datetime(df.index).normalize()).sort_values().unique()
    expected = pd.bdate_range(index.min(), index.max())
    missing = expected.difference(index)
    if missing.empty:
        return []

    gaps: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    start = missing[0]
    previous = missing[0]
    size = 1
    for current in missing[1:]:
        if len(pd.bdate_range(previous, current)) == 2:
            previous = current
            size += 1
            continue
        if size >= max_gap_bdays:
            gaps.append((start, previous))
        start = current
        previous = current
        size = 1

    if size >= max_gap_bdays:
        gaps.append((start, previous))
    return gaps
