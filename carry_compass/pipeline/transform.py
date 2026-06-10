"""Feature transformation: build the carry/vol panel from cached prices.

Reads raw prices from the SQLite cache and runs the full feature pipeline
(carry computation, realized vol, panel assembly). The result is a tidy
long-format DataFrame ready for regime inference.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from loguru import logger

from carry_compass.cache.dao import PriceCache
from carry_compass.config import load_config
from carry_compass.vol.panel import build_carry_vol_panel


def build_prices_from_cache(
    cache: PriceCache | None = None,
    lookback_days: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Read all universe prices from the SQLite cache.

    Args:
        cache: PriceCache instance. Created from config when None.
        lookback_days: Number of days of history to read. Defaults to config value.

    Returns:
        Dict of {ticker: OHLCV DataFrame} for tickers with cached data.
    """
    cfg = load_config()
    if cache is None:
        cache = PriceCache(cfg.cache.sqlite_path)
    effective_days = lookback_days or cfg.fetch.history_days

    start = date.today() - timedelta(days=effective_days)
    prices: dict[str, pd.DataFrame] = {}

    for asset in cfg.universe:
        df = cache.read_prices(asset.ticker, start=start)
        if not df.empty:
            prices[asset.ticker] = df

    logger.info("Loaded {} tickers from cache", len(prices))
    return prices


def run_transform(
    prices: dict[str, pd.DataFrame] | None = None,
    cache: PriceCache | None = None,
    lookback_days: int | None = None,
) -> pd.DataFrame:
    """Build the carry/vol panel from cached prices.

    Args:
        prices: Pre-loaded prices dict. Loaded from cache when None.
        cache: PriceCache instance used if prices is None.
        lookback_days: History window for cache reads.

    Returns:
        Long-format panel with date, asset, asset_class, carry, vol, ratio columns.
    """
    if prices is None:
        prices = build_prices_from_cache(cache=cache, lookback_days=lookback_days)

    if not prices:
        logger.warning("No prices available for transformation.")
        return pd.DataFrame()

    panel = build_carry_vol_panel(prices)
    logger.info(
        "Panel built: {} rows, {} unique assets, dates {} to {}",
        len(panel),
        panel["asset"].nunique() if not panel.empty else 0,
        panel["date"].min() if not panel.empty else "N/A",
        panel["date"].max() if not panel.empty else "N/A",
    )
    return panel
