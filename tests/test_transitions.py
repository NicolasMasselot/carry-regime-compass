import pandas as pd

from carry_compass.regime.classifier import Regime
from carry_compass.regime.transitions import detect_transitions


def _ts(labels: list[Regime]) -> pd.DataFrame:
    return pd.DataFrame({"regime": labels}, index=pd.bdate_range("2025-01-01", periods=len(labels)))


def test_no_transition_on_flicker() -> None:
    labels = [Regime.MID_CYCLE] * 10 + [Regime.RISK_ON] * 2 + [Regime.MID_CYCLE] * 10

    assert detect_transitions(_ts(labels)) == []


def test_transition_after_smoothing_window() -> None:
    labels = [Regime.MID_CYCLE] * 10 + [Regime.RISK_ON] * 7

    transitions = detect_transitions(_ts(labels))

    assert len(transitions) == 1
    assert transitions[0].from_regime == Regime.MID_CYCLE
    assert transitions[0].to_regime == Regime.RISK_ON
