from collections.abc import Iterator
from unittest.mock import patch

import pandas as pd
import pytest

from carry_compass.cache.dao import PriceCache
from carry_compass.data.fetcher import DataFetcher


@pytest.fixture
def patched_yf(sample_prices: pd.DataFrame) -> Iterator[object]:
    yf_frame = sample_prices.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "adj_close": "Adj Close",
            "volume": "Volume",
        }
    )
    with patch("carry_compass.data.fetcher.yf.download", return_value=yf_frame) as mocked:
        yield mocked


def test_cold_fetch_populates_cache(tmp_cache: PriceCache, patched_yf: object) -> None:
    result = DataFetcher(cache=tmp_cache).fetch_history("SPY", force_refresh=True)

    assert result.rows_added > 0
    assert result.source == "network"
    assert tmp_cache.last_date("SPY") is not None


def test_network_failure_falls_back_to_cache(
    tmp_cache: PriceCache,
    sample_prices: pd.DataFrame,
) -> None:
    tmp_cache.upsert_prices("SPY", sample_prices)
    with patch("carry_compass.data.fetcher.yf.download", side_effect=Exception("network down")):
        result = DataFetcher(cache=tmp_cache).fetch_history("SPY", lookback_days=10_000, force_refresh=True)

    assert result.stale is True
    assert result.source == "cache"
    assert len(result.df) == 10
