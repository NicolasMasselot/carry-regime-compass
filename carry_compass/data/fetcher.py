from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from carry_compass.cache import PriceCache
from carry_compass.config import AppConfig, load_config
from carry_compass.data.normalizer import detect_gaps, normalize_yf_frame


@dataclass
class FetchResult:
    """Result of one ticker fetch.

    Attributes:
        ticker: Yahoo ticker requested.
        df: Canonical OHLCV frame served from cache, network or merged data.
        rows_added: Number of rows inserted or updated in cache.
        source: Data source label: cache, network or merged.
        stale: True when fallback cache was served after a network issue.
    """

    ticker: str
    df: pd.DataFrame
    rows_added: int
    source: str
    stale: bool


class DataFetcher:
    """Fetch Yahoo history through a date-only SQLite cache."""

    def __init__(self, cache: PriceCache | None = None) -> None:
        self.cfg: AppConfig = load_config()
        self.cache = cache or PriceCache(self.cfg.cache.sqlite_path)

    def fetch_history(
        self,
        ticker: str,
        lookback_days: int | None = None,
        force_refresh: bool = False,
    ) -> FetchResult:
        """Fetch one ticker history with cache fallback.

        Args:
            ticker: Yahoo Finance ticker.
            lookback_days: Optional override for configured history length.
            force_refresh: If true, bypass freshness checks and hit Yahoo.

        Returns:
            FetchResult with canonical data and stale/source metadata.
        """
        lookback = lookback_days or self.cfg.fetch.history_days
        end = date.today()
        start = end - timedelta(days=lookback)

        cached = self.cache.read_prices(ticker, start=start, end=end)
        last_cached = self.cache.last_date(ticker)
        need_network = force_refresh or self._is_stale(last_cached, end)
        if not need_network:
            return FetchResult(ticker=ticker, df=cached, rows_added=0, source="cache", stale=False)

        fetch_start = (last_cached + timedelta(days=1)) if last_cached else start
        try:
            downloaded = self._download(ticker, fetch_start, end)
        except Exception as exc:
            logger.warning("fetch failed for {}: {}", ticker, exc)
            self.cache.log_fetch(ticker, rows=0, status="error", error=str(exc))
            fallback = self.cache.read_prices(ticker, start=start, end=end)
            return FetchResult(ticker=ticker, df=fallback, rows_added=0, source="cache", stale=True)

        if downloaded.empty and not cached.empty:
            logger.warning("empty network result for {}; serving cached data", ticker)
            self.cache.log_fetch(ticker, rows=0, status="empty")
            return FetchResult(ticker=ticker, df=cached, rows_added=0, source="cache", stale=True)

        rows_added = self.cache.upsert_prices(ticker, downloaded)
        status = "ok" if not downloaded.empty else "empty"
        self.cache.log_fetch(ticker, rows=len(downloaded), status=status)

        merged = self.cache.read_prices(ticker, start=start, end=end)
        gaps = detect_gaps(merged)
        if gaps:
            logger.warning("remaining gaps for {}: {}", ticker, gaps)

        source = "merged" if not cached.empty else "network"
        return FetchResult(
            ticker=ticker,
            df=merged,
            rows_added=rows_added,
            source=source,
            stale=False,
        )

    @staticmethod
    def _is_stale(last_cached: date | None, today: date) -> bool:
        if last_cached is None:
            return True
        last_business_day = pd.bdate_range(end=today, periods=2)[0].date()
        return last_cached < last_business_day

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _download(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        raw = yf.download(
            ticker,
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            progress=False,
            auto_adjust=False,
            threads=False,
            timeout=self.cfg.fetch.request_timeout_s,
        )
        return normalize_yf_frame(raw, ticker)
