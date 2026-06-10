from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

REGIME_MEANINGS: dict[str, str] = {
    "Risk-On": (
        "Cross-asset carry is rich and volatility is calm: "
        "markets are broadly rewarding risk-taking."
    ),
    "Mid-Cycle": (
        "Carry and volatility are both near long-run averages: "
        "no strong signal in either direction."
    ),
    "Late-Cycle": (
        "Carry is still positive but volatility is rising: "
        "conditions are becoming more fragile."
    ),
    "Deleveraging": (
        "Volatility has spiked and carry has collapsed: "
        "cross-asset conditions are flagging broad market stress."
    ),
}

REGIME_RECOMMENDATIONS: dict[str, str] = {
    "Risk-On": "Favor carry and risk assets; the volatility environment is supportive.",
    "Mid-Cycle": "Hold balanced positions; no strong directional tilt is warranted.",
    "Late-Cycle": "Trim tail risk; monitor carry crowding as volatility builds.",
    "Deleveraging": "Reduce carry exposure; conditions signal a risk-off deleveraging state.",
}


@dataclass(frozen=True)
class HeadlineCall:
    """All fields needed to render the top-of-page decision card."""

    regime: str
    meaning: str
    recommendation: str
    confidence: float
    streak_days: int
    carry_z: float
    vol_z: float
    as_of: str


def _compute_confidence(regime: str, latest: pd.DataFrame) -> float:
    """Fraction of assets whose carry/vol ratio sign aligns with the regime.

    DELEVERAGING is aligned by negative ratio; all other regimes by positive ratio.
    """
    if latest.empty or "ratio" not in latest.columns:
        return 0.0
    ratios = latest["ratio"].dropna()
    if ratios.empty:
        return 0.0
    if regime == "Deleveraging":
        aligned = int((ratios <= 0).sum())
    else:
        aligned = int((ratios > 0).sum())
    return aligned / len(ratios)


def _compute_streak(regimes: pd.DataFrame, current_regime: str) -> int:
    """Count consecutive tail days holding the current smoothed regime label."""
    if regimes.empty:
        return 0
    col = "regime_smoothed" if "regime_smoothed" in regimes.columns else "regime"
    streak = 0
    for raw in reversed(list(regimes[col])):
        label = str(getattr(raw, "value", raw))
        if label == current_regime:
            streak += 1
        else:
            break
    return streak


def build_headline_call(
    regimes: pd.DataFrame,
    latest_cross_section: pd.DataFrame,
) -> HeadlineCall:
    """Build the headline call from current regime state and latest asset cross-section.

    Args:
        regimes: Date-indexed frame with regime_smoothed (or regime) and carry_z, vol_z columns.
        latest_cross_section: Latest per-asset panel rows with carry, vol, ratio columns.

    Returns:
        HeadlineCall with all display fields populated.
    """
    if regimes.empty:
        return HeadlineCall(
            regime="Unknown",
            meaning="No regime data is available.",
            recommendation="Check the data pipeline.",
            confidence=0.0,
            streak_days=0,
            carry_z=0.0,
            vol_z=0.0,
            as_of="--",
        )

    last = regimes.iloc[-1]
    col = "regime_smoothed" if "regime_smoothed" in regimes.columns else "regime"
    regime = str(getattr(last[col], "value", last[col]))
    as_of = pd.Timestamp(regimes.index[-1]).strftime("%Y-%m-%d")

    return HeadlineCall(
        regime=regime,
        meaning=REGIME_MEANINGS.get(regime, ""),
        recommendation=REGIME_RECOMMENDATIONS.get(regime, ""),
        confidence=_compute_confidence(regime, latest_cross_section),
        streak_days=_compute_streak(regimes, regime),
        carry_z=float(last["carry_z"]),
        vol_z=float(last["vol_z"]),
        as_of=as_of,
    )
