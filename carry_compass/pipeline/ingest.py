"""Data ingestion: Yahoo Finance prices and FRED macro series.

Environment variables:
    FRED_API_KEY: Required for FRED ingestion. If not set, FRED is skipped
                  with a warning. Set this in Streamlit secrets (secrets.toml)
                  or as an environment variable.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

from loguru import logger

from carry_compass.cache.dao import PriceCache
from carry_compass.config import load_config
from carry_compass.data.batch import fetch_universe


def _ingest_fred(cache: PriceCache, lookback_days: int = 400) -> dict[str, int]:
    """Pull configured FRED series into the macro_series SQLite table.

    Args:
        cache: PriceCache instance for writing macro observations.
        lookback_days: How far back to fetch each series.

    Returns:
        Dict of {series_id: rows_upserted}.
    """
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        logger.warning(
            "FRED_API_KEY not set; skipping FRED ingestion. "
            "Set the key in your environment or Streamlit secrets.toml."
        )
        return {}

    try:
        import fredapi  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("fredapi not installed; skipping FRED ingestion.")
        return {}

    cfg = load_config()
    if not cfg.fred.series:
        logger.info("No FRED series configured in universe.yaml; skipping.")
        return {}

    fred = fredapi.Fred(api_key=api_key)
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    results: dict[str, int] = {}

    for series_cfg in cfg.fred.series:
        try:
            data = fred.get_series(series_cfg.id, observation_start=start)
            rows = cache.upsert_macro(series_cfg.id, data)
            results[series_cfg.id] = rows
            logger.info("FRED {}: {} rows upserted", series_cfg.id, rows)
        except Exception as exc:
            logger.warning("FRED {} fetch failed: {}", series_cfg.id, exc)
            results[series_cfg.id] = 0

    return results


def run_ingest(
    force_refresh: bool = False,
    lookback_days: int | None = None,
) -> dict:
    """Run full ingestion: Yahoo Finance prices and FRED macro series.

    Args:
        force_refresh: If True, bypass Yahoo cache freshness checks.
        lookback_days: Optional override for price history window.

    Returns:
        Summary dict with keys "prices" (FetchResult dict) and "fred" (rows upserted per series).
    """
    cfg = load_config()
    effective_days = lookback_days or cfg.fetch.history_days
    logger.info("Starting price ingestion ({} days lookback)", effective_days)

    price_results = fetch_universe(
        force_refresh=force_refresh,
        lookback_days=lookback_days,
    )
    fetched = sum(1 for r in price_results.values() if not r.df.empty)
    stale = sum(1 for r in price_results.values() if r.stale)
    logger.info("Price ingestion complete: {}/{} tickers, {} stale", fetched, len(price_results), stale)

    cache = PriceCache(cfg.cache.sqlite_path)
    fred_results = _ingest_fred(cache, lookback_days=effective_days)

    return {"prices": price_results, "fred": fred_results}
