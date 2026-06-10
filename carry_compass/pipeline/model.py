"""Regime inference: centroid computation, classification, and smoothing.

Takes the carry/vol panel produced by transform.py and outputs a date-indexed
regime DataFrame ready for the dashboard and backtest layers.
"""
from __future__ import annotations

import pandas as pd
from loguru import logger

from carry_compass.regime.centroid import compute_centroid
from carry_compass.regime.classifier import regime_timeseries
from carry_compass.regime.transitions import smoothed_regime


def run_inference(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute regime labels from a carry/vol panel.

    Args:
        panel: Long-format panel with carry_z and vol_z columns (output of transform.py).

    Returns:
        Date-indexed DataFrame with carry_z, vol_z, regime, and regime_smoothed columns.
        Empty DataFrame when the panel has too few rows to compute z-scores.
    """
    if panel.empty:
        logger.warning("Empty panel passed to run_inference; returning empty result.")
        return pd.DataFrame()

    centroid = compute_centroid(panel)
    if centroid.empty:
        logger.warning("Centroid computation returned empty result.")
        return pd.DataFrame()

    regimes = regime_timeseries(centroid)
    regimes["regime_smoothed"] = smoothed_regime(regimes)

    current = str(getattr(regimes["regime_smoothed"].iloc[-1], "value", regimes["regime_smoothed"].iloc[-1]))
    logger.info(
        "Inference complete: {} regime-days, current regime: {}",
        len(regimes),
        current,
    )
    return regimes
