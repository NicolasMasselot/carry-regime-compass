from dataclasses import dataclass
from datetime import date

import pandas as pd

from carry_compass.config import load_config
from carry_compass.regime.classifier import Regime


@dataclass(frozen=True)
class Transition:
    """Confirmed regime transition after the smoothing window."""

    from_regime: Regime
    to_regime: Regime
    confirmed_at: date


def detect_transitions(regimes: pd.DataFrame) -> list[Transition]:
    """Find confirmed regime transitions in a raw regime time series.

    Args:
        regimes: Date-indexed frame containing a ``regime`` column.

    Returns:
        Chronological list of transitions confirmed after the configured
        smoothing streak length.
    """
    if regimes.empty:
        return []

    k = load_config().regime.transition_smoothing_days
    labels = list(regimes["regime"])
    dates = list(regimes.index)
    confirmed = labels[0]
    streak_label = labels[0]
    streak = 1
    transitions: list[Transition] = []

    for i, label in enumerate(labels[1:], start=1):
        if label == streak_label:
            streak += 1
        else:
            streak_label = label
            streak = 1

        if streak >= k and streak_label != confirmed:
            transitions.append(
                Transition(
                    from_regime=confirmed,
                    to_regime=streak_label,
                    confirmed_at=pd.Timestamp(dates[i]).date(),
                )
            )
            confirmed = streak_label

    return transitions


def smoothed_regime(regimes: pd.DataFrame) -> pd.Series:
    """Apply the anti-flicker smoothing rule to raw regime labels.

    Args:
        regimes: Date-indexed frame containing a ``regime`` column.

    Returns:
        Series of confirmed regime labels, changing only after a sustained
        streak of the new raw regime.
    """
    if regimes.empty:
        return pd.Series(dtype="object", name="regime_smoothed")

    k = load_config().regime.transition_smoothing_days
    labels = list(regimes["regime"])
    confirmed = labels[0]
    streak_label = labels[0]
    streak = 1
    smoothed = [confirmed]

    for label in labels[1:]:
        if label == streak_label:
            streak += 1
        else:
            streak_label = label
            streak = 1

        if streak >= k:
            confirmed = streak_label
        smoothed.append(confirmed)

    return pd.Series(smoothed, index=regimes.index, name="regime_smoothed")
