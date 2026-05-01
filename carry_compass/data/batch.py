from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from carry_compass.config import load_config
from carry_compass.data.fetcher import DataFetcher, FetchResult


def fetch_universe(force_refresh: bool = False, max_workers: int = 4) -> dict[str, FetchResult]:
    """Fetch the configured universe concurrently.

    Args:
        force_refresh: If true, request fresh Yahoo data for every ticker.
        max_workers: Thread pool size, kept low to reduce Yahoo rate-limit risk.

    Returns:
        Mapping of successfully fetched tickers to FetchResult objects. Ticker
        failures are logged and omitted so the dashboard can continue partially.
    """
    cfg = load_config()
    fetcher = DataFetcher()
    results: dict[str, FetchResult] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetcher.fetch_history, asset.ticker, None, force_refresh): asset.ticker
            for asset in cfg.universe
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                results[ticker] = future.result()
            except Exception as exc:
                logger.exception("unrecoverable fetch error for {}: {}", ticker, exc)

    return results
