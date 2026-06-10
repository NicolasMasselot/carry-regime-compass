"""Explicit no-lookahead test for the backtest engine.

The core invariant: the regime applied on day t must equal the smoothed
regime from day t-1. No future information may enter the allocation decision.
"""

import pandas as pd
import pytest

from carry_compass.backtest.engine import run_backtest
from carry_compass.regime.classifier import Regime


def _make_prices(dates: pd.DatetimeIndex, n_assets: int = 4) -> dict[str, pd.DataFrame]:
    """Synthetic OHLCV frames with constant price (no vol, trivial returns)."""
    import numpy as np

    tickers = [f"FAKE{i}=F" for i in range(n_assets)]
    result = {}
    for ticker in tickers:
        close = pd.Series(100.0, index=dates)
        result[ticker] = pd.DataFrame(
            {"open": close, "high": close, "low": close, "close": close, "adj_close": close, "volume": 0.0},
            index=dates,
        )
    return result


def _make_regimes(dates: pd.DatetimeIndex) -> pd.DataFrame:
    labels = [
        Regime.RISK_ON, Regime.RISK_ON, Regime.MID_CYCLE, Regime.LATE_CYCLE,
        Regime.DELEVERAGING, Regime.DELEVERAGING, Regime.MID_CYCLE, Regime.RISK_ON,
        Regime.RISK_ON, Regime.MID_CYCLE,
    ]
    # Cycle the labels to fill all dates
    cycled = [labels[i % len(labels)] for i in range(len(dates))]
    df = pd.DataFrame(
        {
            "carry_z": 0.6,
            "vol_z": -0.3,
            "n_assets": 4,
            "regime": cycled,
        },
        index=dates,
    )
    df["regime_smoothed"] = df["regime"]
    return df


def _make_panel(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for d in dates:
        for asset in ["FAKE0", "FAKE1", "FAKE2", "FAKE3"]:
            rows.append({"date": d, "asset": asset, "asset_class": "equity", "carry": 0.05, "vol": 0.10, "ratio": 0.5})
    return pd.DataFrame(rows)


class _MinimalConfig:
    """Minimal config substitute for tests."""

    class _FetchCfg:
        history_days = 400

    class _VolCfg:
        window_days = 5
        annualization_factor = 252
        min_observations = 3

    class _RegimeCfg:
        transition_smoothing_days = 2

    class _CacheCfg:
        sqlite_path = "data/cache/prices_test.db"

    fetch = _FetchCfg()
    vol = _VolCfg()
    regime = _RegimeCfg()
    cache = _CacheCfg()


def _make_fake_universe(n: int = 4):
    from unittest.mock import MagicMock
    from carry_compass.config.schema import AssetClass

    assets = []
    for i in range(n):
        a = MagicMock()
        a.ticker = f"FAKE{i}=F"
        a.label = f"FAKE{i}"
        a.asset_class = AssetClass.COMMODITY
        a.role = "primary"
        assets.append(a)
    return assets


@pytest.fixture
def backtest_inputs():
    dates = pd.bdate_range("2024-01-02", periods=30)
    prices = _make_prices(dates, n_assets=4)
    regimes = _make_regimes(dates)
    panel = _make_panel(dates)
    return dates, prices, regimes, panel


def test_no_lookahead(backtest_inputs, monkeypatch):
    """regimes_used[t] must equal regime_smoothed[t-1] for all t > first day."""
    dates, prices, regimes, panel = backtest_inputs

    # Patch load_config so build_return_matrix uses our synthetic universe
    from unittest.mock import MagicMock
    import carry_compass.backtest.returns as ret_module

    fake_cfg = MagicMock()
    fake_cfg.universe = _make_fake_universe(4)
    monkeypatch.setattr(ret_module, "load_config", lambda: fake_cfg)

    result = run_backtest(
        regimes=regimes,
        panel=panel,
        prices=prices,
        cfg=fake_cfg,
        oos_start=pd.Timestamp("2024-01-20"),
        tc_bps=0.0,
    )

    assert not result.portfolio.empty, "backtest returned empty result"

    smoothed = regimes["regime_smoothed"].map(lambda v: str(getattr(v, "value", v)))
    smoothed_shifted = smoothed.shift(1)

    # For every date with a valid shifted regime, regimes_used must match
    for date in result.regimes_used.index:
        expected = smoothed_shifted.get(date)
        if pd.isna(expected):
            # First day: no prior regime, defaults to Mid-Cycle
            assert result.regimes_used[date] == "Mid-Cycle", (
                f"First day {date}: expected Mid-Cycle fallback, got {result.regimes_used[date]}"
            )
        else:
            actual = result.regimes_used[date]
            assert actual == str(expected), (
                f"Lookahead detected on {date}: regime_used={actual!r} "
                f"but regime_smoothed[t-1]={expected!r}"
            )


def test_deleveraging_is_cash(backtest_inputs, monkeypatch):
    """In Deleveraging regime, all weights must be zero (100% cash)."""
    dates, prices, regimes, panel = backtest_inputs

    from unittest.mock import MagicMock
    import carry_compass.backtest.returns as ret_module

    fake_cfg = MagicMock()
    fake_cfg.universe = _make_fake_universe(4)
    monkeypatch.setattr(ret_module, "load_config", lambda: fake_cfg)

    result = run_backtest(
        regimes=regimes,
        panel=panel,
        prices=prices,
        cfg=fake_cfg,
        oos_start=pd.Timestamp("2024-01-20"),
        tc_bps=0.0,
    )

    if result.weights.empty:
        pytest.skip("No weights available")

    deleverage_dates = result.regimes_used[result.regimes_used == "Deleveraging"].index
    for date in deleverage_dates:
        if date in result.weights.index:
            row = result.weights.loc[date]
            assert row.sum() == pytest.approx(0.0, abs=1e-9), (
                f"Expected zero weights in Deleveraging on {date}, got {row.sum():.6f}"
            )
