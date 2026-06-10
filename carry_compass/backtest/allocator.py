from __future__ import annotations

import pandas as pd


def regime_weights(
    regime: str,
    asset_labels: list[str],
    carry_ratios: pd.Series | None = None,
    top_n_risk_on: int = 5,
) -> dict[str, float]:
    """Portfolio weights for one day given a regime label.

    Allocation rule:
      - Deleveraging: 100% cash, all weights zero.
      - Risk-On: equal-weight the top N assets by carry/vol ratio.
        Falls back to equal-weight all if carry_ratios is unavailable.
      - Mid-Cycle / Late-Cycle: equal-weight all assets.

    The rule is intentionally simple so that performance reflects the regime
    signal, not a complex strategy layer on top of it.

    Args:
        regime: Regime label string (e.g. "Risk-On", "Deleveraging").
        asset_labels: All tradeable assets in the backtest universe.
        carry_ratios: Series indexed by asset label with carry/vol ratios
                      from yesterday's panel. Used to rank in Risk-On.
        top_n_risk_on: Maximum number of top-carry assets held in Risk-On.

    Returns:
        Dict {asset_label: weight}. Weights sum to 1.0 when invested, 0.0
        in Deleveraging (cash).
    """
    if not asset_labels:
        return {}

    if regime == "Deleveraging":
        return {label: 0.0 for label in asset_labels}

    if regime == "Risk-On" and carry_ratios is not None:
        valid = carry_ratios.reindex(asset_labels).dropna()
        top = valid.nlargest(min(top_n_risk_on, len(valid)))
        if not top.empty:
            w = 1.0 / len(top)
            return {label: (w if label in top.index else 0.0) for label in asset_labels}

    # Mid-Cycle and Late-Cycle: equal-weight all
    w = 1.0 / len(asset_labels)
    return {label: w for label in asset_labels}
