from functools import lru_cache

import pandas as pd
import yfinance as yf
from loguru import logger

from carry_compass.config import load_config
from carry_compass.config.schema import AssetClass

EQUITY_PE_FALLBACK = {"^GSPC": 22.0, "^STOXX50E": 14.0, "^N225": 18.0, "^FTSE": 12.0}


@lru_cache(maxsize=32)
def _trailing_pe(ticker: str, fallback: float) -> float:
    try:
        raw = yf.Ticker(ticker).info.get("trailingPE")
        logger.debug("{} raw trailing PE from yfinance: {}", ticker, raw)
        if raw is None:
            return fallback
        value = float(raw)
        return value if value > 0 else fallback
    except Exception as exc:
        logger.warning("failed to fetch trailing PE for {}: {}", ticker, exc)
        return fallback


def compute_equity_carry(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute equity carry as earnings yield minus short risk-free rate.

    Args:
        prices: Mapping containing equity index frames and ``^IRX``.

    Returns:
        Wide date x equity-label frame of annualized decimal carry.

    Notes:
        Earnings yield is ``1 / trailing P/E`` from Yahoo info. P/E is held
        constant historically; production work would use a point-in-time series.
    """
    if "^IRX" not in prices:
        raise ValueError("equity carry requires ^IRX in prices")

    cfg = load_config()
    rf = prices["^IRX"]["close"] / 100.0
    out: dict[str, pd.Series] = {}
    for asset in cfg.universe:
        if asset.asset_class != AssetClass.EQUITY or asset.ticker not in prices:
            continue
        pe = _trailing_pe(asset.ticker, EQUITY_PE_FALLBACK[asset.ticker])
        earnings_yield = 1.0 / pe
        common = prices[asset.ticker].index.intersection(rf.index)
        out[asset.label] = earnings_yield - rf.reindex(common)

    return pd.DataFrame(out).sort_index()
