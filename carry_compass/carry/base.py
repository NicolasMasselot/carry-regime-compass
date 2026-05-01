from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CarryResult:
    """Container for a carry block returned by an asset-class module.

    Attributes:
        asset_class: Internal asset-class key.
        df: Wide date x asset carry frame in annualized decimal units.
    """

    asset_class: str
    df: pd.DataFrame


def safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    """Divide two aligned series while treating zero denominators as missing.

    Args:
        a: Numerator series.
        b: Denominator series, where zeros are replaced by NA.

    Returns:
        Elementwise ratio with pandas NA propagation.
    """
    return a.divide(b.replace(0, pd.NA))
