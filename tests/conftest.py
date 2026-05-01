from pathlib import Path

import pandas as pd
import pytest

from carry_compass.cache.dao import PriceCache


def make_price_frame(close: float, periods: int = 10) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-01", periods=periods)
    return pd.DataFrame(
        {
            "open": [close] * periods,
            "high": [close] * periods,
            "low": [close] * periods,
            "close": [close] * periods,
            "adj_close": [close] * periods,
            "volume": [1_000_000.0] * periods,
        },
        index=index,
    )


@pytest.fixture
def tmp_cache(tmp_path: Path) -> PriceCache:
    return PriceCache(tmp_path / "test.db")


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    index = pd.bdate_range("2025-01-01", periods=10)
    return pd.DataFrame(
        {
            "open": [100.0] * 10,
            "high": [101.0] * 10,
            "low": [99.0] * 10,
            "close": [100.5] * 10,
            "adj_close": [100.5] * 10,
            "volume": [1_000_000.0] * 10,
        },
        index=index,
    )
