from __future__ import annotations

import pandas as pd

from carry_compass.config import load_config
from carry_compass.config.schema import AppConfig

# EM FX pairs: the carry trade is LONG the EM currency, SHORT USD.
# The Yahoo price is quoted as USD per EM unit (USDBRL = BRL per USD, so
# price rising means BRL weakens). We flip the sign so that a rising EM
# carry trade (BRL strengthening) shows as a positive return.
_INVERTED_FX_LABELS: frozenset[str] = frozenset(
    ["USD/BRL", "USD/MXN", "USD/TRY", "USD/ZAR"]
)

# Pure yield series from Yahoo (^IRX, ^FVX, ^TNX, ^TYX) represent interest-rate
# levels, not tradeable price time series. Excluded from the return matrix.
_YIELD_TICKERS: frozenset[str] = frozenset(["^IRX", "^FVX", "^TNX", "^TYX"])


def build_return_matrix(
    prices: dict[str, pd.DataFrame],
    cfg: AppConfig | None = None,
) -> pd.DataFrame:
    """Daily simple returns for the tradeable primary-role asset universe.

    Yield tickers are excluded (not directly investable). EM FX pairs are
    sign-flipped so positive return = positive carry-trade P&L. All other
    assets use (price_t / price_{t-1}) - 1 on adjusted close.

    Args:
        prices: Dict of {ticker: OHLCV DataFrame} from fetch_universe.
        cfg: App config. Loaded from universe.yaml when None.

    Returns:
        Wide DataFrame indexed by date, one column per tradeable asset label.
        Cells are NaN on dates with no price observation.
    """
    if cfg is None:
        cfg = load_config()

    tradeable = [
        a for a in cfg.universe
        if a.role == "primary" and a.ticker not in _YIELD_TICKERS
    ]

    frames: dict[str, pd.Series] = {}
    for asset in tradeable:
        df = prices.get(asset.ticker)
        if df is None or df.empty:
            continue
        col = (
            "adj_close"
            if "adj_close" in df.columns and df["adj_close"].notna().any()
            else "close"
        )
        close = df[col].dropna()
        if len(close) < 2:
            continue
        ret = close.pct_change()
        if asset.label in _INVERTED_FX_LABELS:
            ret = -ret
        frames[asset.label] = ret

    if not frames:
        return pd.DataFrame()

    result = pd.DataFrame(frames)
    result.index = pd.DatetimeIndex(result.index)
    result.index.name = "date"
    return result
