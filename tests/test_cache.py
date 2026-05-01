from datetime import date

import pandas as pd

from carry_compass.cache.dao import PriceCache


def test_round_trip_insert_read(tmp_cache: PriceCache, sample_prices: pd.DataFrame) -> None:
    inserted = tmp_cache.upsert_prices("SPY", sample_prices)
    result = tmp_cache.read_prices("SPY")

    assert inserted == 10
    assert len(result) == 10
    assert result.index.name == "date"
    assert result["close"].iloc[0] == 100.5


def test_idempotent_upsert_keeps_row_count(
    tmp_cache: PriceCache, sample_prices: pd.DataFrame
) -> None:
    tmp_cache.upsert_prices("SPY", sample_prices)
    tmp_cache.upsert_prices("SPY", sample_prices)

    assert len(tmp_cache.read_prices("SPY")) == 10


def test_last_date_returns_latest_date(tmp_cache: PriceCache, sample_prices: pd.DataFrame) -> None:
    tmp_cache.upsert_prices("SPY", sample_prices)

    assert tmp_cache.last_date("SPY") == date(2025, 1, 14)


def test_purge_wipes_table(tmp_cache: PriceCache, sample_prices: pd.DataFrame) -> None:
    tmp_cache.upsert_prices("SPY", sample_prices)

    assert tmp_cache.purge() == 10
    assert tmp_cache.read_prices("SPY").empty
