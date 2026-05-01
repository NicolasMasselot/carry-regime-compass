from enum import Enum

import pandas as pd

from carry_compass.config import load_config
from carry_compass.config.schema import RegimeThresholds


class Regime(str, Enum):
    """Macro regimes inferred from cross-asset carry and volatility."""

    RISK_ON = "Risk-On"
    MID_CYCLE = "Mid-Cycle"
    LATE_CYCLE = "Late-Cycle"
    DELEVERAGING = "Deleveraging"


def classify_row(carry_z: float, vol_z: float, t: RegimeThresholds) -> Regime:
    """Classify one carry/vol z-score pair into a macro regime.

    Args:
        carry_z: Time-series z-score of median cross-asset carry.
        vol_z: Time-series z-score of median cross-asset realized volatility.
        t: Threshold configuration loaded from ``universe.yaml``.

    Returns:
        One of the four dashboard regimes. Deleveraging is evaluated first so a
        volatility spike with weak carry is not mislabeled as Late-Cycle.
    """
    if vol_z >= t.deleveraging_vol_z_min and carry_z <= t.deleveraging_carry_z_max:
        return Regime.DELEVERAGING
    if carry_z >= t.risk_on_carry_z_min and vol_z <= t.risk_on_vol_z_max:
        return Regime.RISK_ON
    if carry_z >= 0 and vol_z > t.risk_on_vol_z_max:
        return Regime.LATE_CYCLE
    return Regime.MID_CYCLE


def regime_timeseries(centroid: pd.DataFrame) -> pd.DataFrame:
    """Attach raw regime labels to a centroid time series.

    Args:
        centroid: Date-indexed frame with ``carry_z`` and ``vol_z`` columns.

    Returns:
        Copy of the centroid with a ``regime`` column of ``Regime`` enum values.
    """
    cfg = load_config()
    regimes = centroid.copy()
    regimes["regime"] = [
        classify_row(row.carry_z, row.vol_z, cfg.regime)
        for row in regimes[["carry_z", "vol_z"]].itertuples(index=False)
    ]
    return regimes
