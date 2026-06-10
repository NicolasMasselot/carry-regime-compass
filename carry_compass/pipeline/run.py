"""Pipeline CLI entry point.

Runs the full pipeline: ingest -> transform -> inference -> parquet snapshot.

Usage:
    python -m carry_compass.pipeline.run
    python -m carry_compass.pipeline.run --force
    python -m carry_compass.pipeline.run --lookback 1500

The pipeline writes a versioned parquet snapshot under data/snapshots/ that
the Streamlit app reads on startup. This decouples the ingestion schedule
(daily GitHub Action) from the rendering layer (Streamlit).

FRED ingestion requires FRED_API_KEY in the environment or .env file.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from loguru import logger

from carry_compass.config import load_config
from carry_compass.pipeline.ingest import run_ingest
from carry_compass.pipeline.model import run_inference
from carry_compass.pipeline.transform import build_prices_from_cache, run_transform
from carry_compass.utils.logging import configure_logging


def _write_snapshot(
    prices: dict[str, pd.DataFrame],
    snapshot_dir: Path,
    today: date | None = None,
) -> Path:
    """Write prices as a wide adj_close parquet snapshot.

    The file is named prices_YYYY-MM-DD.parquet. The date index and ticker
    columns make it easy to reconstruct the prices dict in the app.

    Args:
        prices: Dict of {ticker: OHLCV DataFrame}.
        snapshot_dir: Directory to write the file into.
        today: Override the date used in the filename (default: today).

    Returns:
        Path of the written file.
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    as_of = today or date.today()

    frames = {}
    for ticker, df in prices.items():
        if df.empty:
            continue
        col = "adj_close" if "adj_close" in df.columns and df["adj_close"].notna().any() else "close"
        frames[ticker] = df[col].rename(ticker)

    if not frames:
        logger.warning("No price data to write to snapshot.")
        raise ValueError("Empty prices dict; nothing to snapshot.")

    wide = pd.DataFrame(frames)
    wide.index = pd.DatetimeIndex(wide.index)
    wide.index.name = "date"
    wide.sort_index(inplace=True)

    path = snapshot_dir / f"prices_{as_of.isoformat()}.parquet"
    wide.to_parquet(path, compression="snappy")
    size_kb = path.stat().st_size / 1024
    logger.info("Snapshot written: {} ({:.1f} KB, {} tickers, {} dates)", path, size_kb, len(frames), len(wide))
    return path


def main(argv: list[str] | None = None) -> int:
    configure_logging()

    parser = argparse.ArgumentParser(description="Run the carry regime compass pipeline.")
    parser.add_argument("--force", action="store_true", help="Force fresh data fetch from Yahoo.")
    parser.add_argument("--lookback", type=int, default=None, help="Override history window in days.")
    args = parser.parse_args(argv)

    cfg = load_config()
    snapshot_dir = Path("data/snapshots")

    logger.info("=== Carry Regime Compass Pipeline ===")

    # 1. Ingest
    logger.info("Step 1/4: Ingesting data")
    ingest_result = run_ingest(force_refresh=args.force, lookback_days=args.lookback)
    price_results = ingest_result["prices"]
    prices = {
        ticker: result.df
        for ticker, result in price_results.items()
        if not result.df.empty
    }

    if not prices:
        logger.error("No prices fetched. Pipeline aborted.")
        return 1

    # 2. Transform
    logger.info("Step 2/4: Building feature panel")
    panel = run_transform(prices=prices)
    if panel.empty:
        logger.error("Panel is empty after transformation. Pipeline aborted.")
        return 1

    # 3. Inference
    logger.info("Step 3/4: Running regime inference")
    regimes = run_inference(panel)
    if regimes.empty:
        logger.error("Regime inference produced empty result. Pipeline aborted.")
        return 1

    # 4. Write snapshot
    logger.info("Step 4/4: Writing parquet snapshot")
    _write_snapshot(prices, snapshot_dir)

    logger.info("=== Pipeline complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
