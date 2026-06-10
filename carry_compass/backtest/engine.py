from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from carry_compass.backtest.allocator import regime_weights
from carry_compass.backtest.returns import build_return_matrix
from carry_compass.config.schema import AppConfig


@dataclass
class BacktestResult:
    """Outputs of run_backtest."""

    portfolio: pd.Series    # daily portfolio simple returns
    benchmark: pd.Series    # daily equal-weight benchmark simple returns
    weights: pd.DataFrame   # daily allocation (date x asset_label)
    regimes_used: pd.Series  # regime label applied each day (from t-1)
    oos_start: pd.Timestamp  # first date of the out-of-sample window


def run_backtest(
    regimes: pd.DataFrame,
    panel: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
    cfg: AppConfig | None = None,
    oos_start: pd.Timestamp | None = None,
    tc_bps: float = 5.0,
    top_n_risk_on: int = 5,
) -> BacktestResult:
    """Walk-forward regime-conditional backtest versus equal-weight benchmark.

    No-lookahead guarantee: the allocation on day t is derived entirely from
    information available at the close of day t-1.

      - Regime label: regime_smoothed.shift(1) - yesterday's confirmed state.
      - Carry ranking: panel carry/vol ratios shifted by 1 day.
      - Returns on day t are the only forward-looking input.

    Transaction costs are deducted as: turnover * tc_bps / 10_000, where
    turnover = sum of absolute portfolio weight changes day over day.

    Args:
        regimes: Date-indexed frame with regime_smoothed (or regime) column.
        panel: Long-format panel with date, asset, ratio columns.
        prices: Dict of {ticker: OHLCV DataFrame} from fetch_universe.
        cfg: App config; loaded from universe.yaml when None.
        oos_start: First date of the out-of-sample window. Defaults to the
                   midpoint of the available history.
        tc_bps: One-way transaction cost in basis points (applied on turnover).
        top_n_risk_on: Assets held in Risk-On regime.

    Returns:
        BacktestResult with portfolio, benchmark, weights, regimes_used, oos_start.
    """
    returns = build_return_matrix(prices, cfg)

    _empty = BacktestResult(
        portfolio=pd.Series(dtype=float, name="portfolio"),
        benchmark=pd.Series(dtype=float, name="benchmark"),
        weights=pd.DataFrame(),
        regimes_used=pd.Series(dtype=str, name="regime_used"),
        oos_start=pd.Timestamp.now(),
    )

    if returns.empty or regimes.empty:
        return _empty

    common = returns.index.intersection(regimes.index)
    if len(common) < 10:
        return _empty

    returns = returns.loc[common]

    # Regime series, shifted one day (no lookahead)
    regime_col = "regime_smoothed" if "regime_smoothed" in regimes.columns else "regime"
    regime_raw = (
        regimes[regime_col]
        .reindex(common)
        .map(lambda v: str(getattr(v, "value", v)))
    )
    regime_lagged = regime_raw.shift(1)

    # Carry/vol ratio panel for ranking, also shifted one day
    ratio_pivot = (
        panel[panel["date"].isin(common)][["date", "asset", "ratio"]]
        .dropna(subset=["ratio"])
        .pivot_table(index="date", columns="asset", values="ratio")
        .reindex(common)
        .shift(1)
    )

    asset_labels = list(returns.columns)
    prev_weights: dict[str, float] = {label: 0.0 for label in asset_labels}

    portf_rets: list[float] = []
    bench_rets: list[float] = []
    all_weights: list[dict[str, float]] = []
    regimes_applied: list[str] = []

    for date in common:
        regime = regime_lagged.get(date)
        if pd.isna(regime):
            regime = "Mid-Cycle"  # default before any confirmed regime

        carry_row = ratio_pivot.loc[date] if date in ratio_pivot.index else None
        weights = regime_weights(
            regime=str(regime),
            asset_labels=asset_labels,
            carry_ratios=carry_row,
            top_n_risk_on=top_n_risk_on,
        )

        # Transaction cost on absolute weight change
        turnover = sum(
            abs(weights.get(lbl, 0.0) - prev_weights.get(lbl, 0.0))
            for lbl in asset_labels
        )
        tc_drag = turnover * tc_bps / 10_000

        day_rets = returns.loc[date]
        portf_r = (
            sum(
                weights.get(lbl, 0.0) * (v if pd.notna(v) else 0.0)
                for lbl, v in day_rets.items()
            )
            - tc_drag
        )

        avail = day_rets.dropna()
        bench_r = float(avail.mean()) if not avail.empty else 0.0

        portf_rets.append(portf_r)
        bench_rets.append(bench_r)
        all_weights.append(weights)
        regimes_applied.append(str(regime))
        prev_weights = weights

    idx = pd.DatetimeIndex(common)
    portfolio_s = pd.Series(portf_rets, index=idx, name="portfolio")
    benchmark_s = pd.Series(bench_rets, index=idx, name="benchmark")
    weights_df = pd.DataFrame(all_weights, index=idx)
    regimes_s = pd.Series(regimes_applied, index=idx, name="regime_used")

    if oos_start is None:
        oos_start = idx[len(idx) // 2]

    return BacktestResult(
        portfolio=portfolio_s,
        benchmark=benchmark_s,
        weights=weights_df,
        regimes_used=regimes_s,
        oos_start=pd.Timestamp(oos_start),
    )
