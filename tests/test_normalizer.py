import pandas as pd

from carry_compass.data.normalizer import CANONICAL_COLS, detect_gaps, normalize_yf_frame


def test_normalize_handles_capitalized_cols() -> None:
    raw = pd.DataFrame(
        {
            "Open": [99.0],
            "High": [101.0],
            "Low": [98.0],
            "Close": [100.0],
            "Adj Close": [100.5],
            "Volume": [1000],
        },
        index=pd.DatetimeIndex(["2025-01-01"]),
    )

    result = normalize_yf_frame(raw, "SPY")

    assert list(result.columns) == CANONICAL_COLS
    assert result["adj_close"].iloc[0] == 100.5


def test_normalize_strips_tz() -> None:
    raw = pd.DataFrame(
        {"Open": [99.0], "High": [101.0], "Low": [98.0], "Close": [100.0], "Volume": [1000]},
        index=pd.DatetimeIndex(["2025-01-01 16:00"], tz="America/New_York"),
    )

    result = normalize_yf_frame(raw, "EURUSD=X")

    assert result.index.tz is None
    assert result.index[0] == pd.Timestamp("2025-01-01")
    assert result["adj_close"].iloc[0] == 100.0


def test_normalize_drops_duplicates() -> None:
    raw = pd.DataFrame(
        {"Close": [100.0, 101.0]},
        index=pd.DatetimeIndex(["2025-01-01 10:00", "2025-01-01 16:00"]),
    )

    result = normalize_yf_frame(raw, "SPY")

    assert len(result) == 1
    assert result["close"].iloc[0] == 101.0


def test_detect_gaps() -> None:
    index = pd.bdate_range("2025-01-01", periods=20).delete(slice(5, 15))
    frame = pd.DataFrame({"close": [100.0] * len(index)}, index=index)

    gaps = detect_gaps(frame, max_gap_bdays=3)

    assert len(gaps) == 1
    assert gaps[0] == (pd.Timestamp("2025-01-08"), pd.Timestamp("2025-01-21"))
