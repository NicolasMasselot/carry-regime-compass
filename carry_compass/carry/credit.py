from functools import lru_cache

import pandas as pd
import yfinance as yf
from loguru import logger

FALLBACK_YIELDS = {"HYG": 0.065, "LQD": 0.045, "IEF": 0.040}


@lru_cache(maxsize=32)
def _ticker_dividend_yield(ticker: str, fallback: float) -> float:
    try:
        info = yf.Ticker(ticker).info
        raw = info.get("yield") or info.get("dividendYield")
        logger.debug("{} raw dividend yield from yfinance: {}", ticker, raw)
        if raw is None:
            return fallback
        value = float(raw)
        if value > 1:
            value /= 100.0
        return value
    except Exception as exc:
        logger.warning("failed to fetch dividend yield for {}: {}", ticker, exc)
        return fallback


def compute_credit_carry(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute credit carry from ETF distribution-yield spreads.

    Args:
        prices: Mapping containing HYG/LQD and IEF price frames.

    Returns:
        Wide date x credit-label frame of annualized decimal carry.

    Notes:
        Formula is HY/IG ETF yield minus IEF yield. This is a practical Yahoo
        proxy, not a true OAS or curve-adjusted spread carry model.
    """
    if "IEF" not in prices:
        raise ValueError("credit carry requires IEF in prices")

    ief_index = prices["IEF"].index
    ief_yield = _ticker_dividend_yield("IEF", FALLBACK_YIELDS["IEF"])
    out: dict[str, pd.Series] = {}
    for ticker, label in (("HYG", "HY ETF"), ("LQD", "IG ETF")):
        if ticker not in prices:
            continue
        common = prices[ticker].index.intersection(ief_index)
        yld = _ticker_dividend_yield(ticker, FALLBACK_YIELDS[ticker])
        out[label] = pd.Series(yld - ief_yield, index=common, dtype="float64")

    return pd.DataFrame(out).sort_index()
