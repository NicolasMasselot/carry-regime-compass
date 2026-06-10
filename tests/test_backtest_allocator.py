"""Unit tests for the regime-conditional allocation rule."""

import pytest
import pandas as pd

from carry_compass.backtest.allocator import regime_weights


ASSETS = ["A", "B", "C", "D", "E"]


def test_deleveraging_all_cash():
    w = regime_weights("Deleveraging", ASSETS)
    assert all(v == 0.0 for v in w.values())
    assert sum(w.values()) == pytest.approx(0.0)


def test_mid_cycle_equal_weight():
    w = regime_weights("Mid-Cycle", ASSETS)
    assert sum(w.values()) == pytest.approx(1.0)
    for v in w.values():
        assert v == pytest.approx(1.0 / len(ASSETS))


def test_late_cycle_equal_weight():
    w = regime_weights("Late-Cycle", ASSETS)
    assert sum(w.values()) == pytest.approx(1.0)
    for v in w.values():
        assert v == pytest.approx(1.0 / len(ASSETS))


def test_risk_on_top_n_selected():
    ratios = pd.Series({"A": 2.5, "B": 1.0, "C": -0.5, "D": 3.1, "E": 0.8})
    w = regime_weights("Risk-On", ASSETS, carry_ratios=ratios, top_n_risk_on=2)
    # Top-2 by ratio: D (3.1), A (2.5)
    assert w["D"] == pytest.approx(0.5)
    assert w["A"] == pytest.approx(0.5)
    assert w["B"] == pytest.approx(0.0)
    assert w["C"] == pytest.approx(0.0)
    assert w["E"] == pytest.approx(0.0)
    assert sum(w.values()) == pytest.approx(1.0)


def test_risk_on_no_ratios_falls_back_to_equal():
    w = regime_weights("Risk-On", ASSETS, carry_ratios=None)
    assert sum(w.values()) == pytest.approx(1.0)
    for v in w.values():
        assert v == pytest.approx(1.0 / len(ASSETS))


def test_risk_on_top_n_larger_than_assets():
    ratios = pd.Series({"A": 1.0, "B": 2.0})
    w = regime_weights("Risk-On", ["A", "B"], carry_ratios=ratios, top_n_risk_on=10)
    assert sum(w.values()) == pytest.approx(1.0)


def test_empty_asset_labels():
    w = regime_weights("Mid-Cycle", [])
    assert w == {}


def test_weights_sum_to_one_for_all_invested_regimes():
    for regime in ["Risk-On", "Mid-Cycle", "Late-Cycle"]:
        ratios = pd.Series({a: float(i) for i, a in enumerate(ASSETS)})
        w = regime_weights(regime, ASSETS, carry_ratios=ratios)
        assert sum(w.values()) == pytest.approx(1.0), f"regime={regime}"
