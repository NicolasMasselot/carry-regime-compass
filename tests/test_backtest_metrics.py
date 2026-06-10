"""Unit tests for backtest metric computations."""

import numpy as np
import pandas as pd
import pytest

from carry_compass.backtest.metrics import compute_metrics, compute_regime_diagnostics


def _flat_series(daily_ret: float, n: int = 252) -> pd.Series:
    idx = pd.bdate_range("2024-01-02", periods=n)
    return pd.Series(daily_ret, index=idx)


def test_annualized_return():
    daily = 0.001  # 0.1% per day
    r = _flat_series(daily)
    m = compute_metrics(r, _flat_series(0.0))
    assert m["portfolio"]["Ann. Return"] == pytest.approx(daily * 252, rel=1e-4)


def test_sharpe_sign_matches_return():
    # Positive annualized return with real vol -> positive Sharpe
    np.random.seed(42)
    idx = pd.bdate_range("2024-01-02", periods=252)
    r = pd.Series(np.random.normal(0.001, 0.01, 252), index=idx)
    m = compute_metrics(r, _flat_series(0.0))
    assert m["portfolio"]["Sharpe Ratio"] > 0


def test_max_drawdown_flat_is_zero():
    r = _flat_series(0.001)
    m = compute_metrics(r, _flat_series(0.0))
    assert m["portfolio"]["Max Drawdown"] == pytest.approx(0.0, abs=1e-9)


def test_max_drawdown_single_drop():
    # One bad day sandwiched by good days
    rets = [0.02, 0.01, -0.10, 0.02, 0.01]
    r = pd.Series(rets, index=pd.bdate_range("2024-01-02", periods=5))
    m = compute_metrics(r, r)
    assert m["portfolio"]["Max Drawdown"] < 0.0


def test_hit_rate_all_positive():
    r = _flat_series(0.001)
    m = compute_metrics(r, _flat_series(0.0))
    assert m["portfolio"]["Hit Rate"] == pytest.approx(1.0)


def test_hit_rate_all_negative():
    r = _flat_series(-0.001)
    m = compute_metrics(r, _flat_series(0.0))
    assert m["portfolio"]["Hit Rate"] == pytest.approx(0.0)


def test_excess_return_and_ir_present():
    r = _flat_series(0.002)
    b = _flat_series(0.001)
    m = compute_metrics(r, b)
    assert "Ann. Excess Return" in m["portfolio"]
    assert "Information Ratio" in m["portfolio"]


def test_benchmark_metrics_populated():
    r = _flat_series(0.001)
    b = _flat_series(0.0005)
    m = compute_metrics(r, b)
    assert "Ann. Return" in m["benchmark"]
    assert "Sharpe Ratio" in m["benchmark"]


def test_empty_series_returns_empty_dicts():
    empty = pd.Series(dtype=float)
    m = compute_metrics(empty, empty)
    assert m["portfolio"] == {}
    assert m["benchmark"] == {}


def test_regime_diagnostics_structure():
    n = 50
    idx = pd.bdate_range("2024-01-02", periods=n)
    rets = pd.Series(np.random.normal(0.001, 0.01, n), index=idx)
    regimes = pd.Series(
        ["Risk-On"] * 20 + ["Deleveraging"] * 10 + ["Mid-Cycle"] * 20,
        index=idx,
        name="regime_used",
    )
    diag = compute_regime_diagnostics(rets, regimes)
    assert set(diag.columns) == {"Regime", "Days", "Ann. Return", "Hit Rate", "Above Median"}
    assert len(diag) == 3
    assert diag["Days"].sum() == n


def test_regime_diagnostics_empty():
    diag = compute_regime_diagnostics(pd.Series(dtype=float), pd.Series(dtype=str))
    assert diag.empty
