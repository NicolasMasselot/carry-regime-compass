from carry_compass.config.schema import RegimeThresholds
from carry_compass.regime.classifier import Regime, classify_row


def test_classify_deleveraging() -> None:
    assert classify_row(carry_z=-1.0, vol_z=2.0, t=RegimeThresholds()) == Regime.DELEVERAGING


def test_classify_risk_on() -> None:
    assert classify_row(carry_z=1.0, vol_z=-0.5, t=RegimeThresholds()) == Regime.RISK_ON


def test_classify_late_cycle() -> None:
    assert classify_row(carry_z=0.5, vol_z=0.3, t=RegimeThresholds()) == Regime.LATE_CYCLE


def test_classify_mid_cycle() -> None:
    assert classify_row(carry_z=0.0, vol_z=-0.5, t=RegimeThresholds()) == Regime.MID_CYCLE
