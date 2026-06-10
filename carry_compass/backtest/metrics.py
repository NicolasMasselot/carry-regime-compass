from __future__ import annotations

import numpy as np
import pandas as pd


def compute_metrics(
    portfolio: pd.Series,
    benchmark: pd.Series,
    ann_factor: int = 252,
) -> dict[str, dict[str, float]]:
    """Standard performance metrics for daily simple-return series.

    Args:
        portfolio: Daily portfolio simple returns.
        benchmark: Daily benchmark simple returns.
        ann_factor: Trading days per year for annualization.

    Returns:
        Dict with "portfolio" and "benchmark" sub-dicts of metric name to float.
    """

    def _calc(r: pd.Series) -> dict[str, float]:
        r = r.dropna()
        if len(r) < 2:
            return {}
        ann_ret = float(r.mean() * ann_factor)
        ann_vol = float(r.std() * np.sqrt(ann_factor))
        sharpe = ann_ret / ann_vol if ann_vol > 0 else float("nan")
        cum = (1 + r).cumprod()
        max_dd = float((cum / cum.cummax() - 1).min())
        hit = float((r > 0).mean())
        return {
            "Ann. Return": ann_ret,
            "Ann. Volatility": ann_vol,
            "Sharpe Ratio": sharpe,
            "Max Drawdown": max_dd,
            "Hit Rate": hit,
        }

    p = _calc(portfolio)
    b = _calc(benchmark)

    if p and b:
        excess = portfolio.sub(benchmark, fill_value=0.0).dropna()
        if len(excess) > 1:
            p["Ann. Excess Return"] = float(excess.mean() * ann_factor)
            ex_vol = float(excess.std() * np.sqrt(ann_factor))
            p["Information Ratio"] = (
                p["Ann. Excess Return"] / ex_vol if ex_vol > 0 else float("nan")
            )

    return {"portfolio": p, "benchmark": b}


def compute_regime_diagnostics(
    portfolio: pd.Series,
    regimes_used: pd.Series,
) -> pd.DataFrame:
    """Per-regime return diagnostics for honest reporting.

    For each regime label, reports: number of days the model was allocated in
    that regime, annualized mean return, hit rate, and fraction of days with
    above-median return across the full sample.

    Args:
        portfolio: Daily portfolio simple returns.
        regimes_used: Regime label applied on each day (from engine output).

    Returns:
        DataFrame with one row per regime, sorted by Ann. Return descending.
    """
    if portfolio.empty or regimes_used.empty:
        return pd.DataFrame()

    df = pd.DataFrame({"return": portfolio, "regime": regimes_used}).dropna()
    if df.empty:
        return pd.DataFrame()

    overall_median = df["return"].median()
    rows = []
    for regime, grp in df.groupby("regime"):
        rows.append(
            {
                "Regime": str(regime),
                "Days": len(grp),
                "Ann. Return": float(grp["return"].mean() * 252),
                "Hit Rate": float((grp["return"] > 0).mean()),
                "Above Median": float((grp["return"] > overall_median).mean()),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("Ann. Return", ascending=False)
        .reset_index(drop=True)
    )
