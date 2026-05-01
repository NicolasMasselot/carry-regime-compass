import pandas as pd

from carry_compass.config import load_config
from carry_compass.config.schema import AssetClass


def compute_rates_carry(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute rates carry as a term-premium proxy.

    Args:
        prices: Mapping containing ``^IRX`` and configured long-rate tickers.

    Returns:
        Wide date x rate-label frame of annualized decimal carry.

    Notes:
        Formula is long yield minus 3M yield. Yahoo yields are percent quotes,
        divided by 100 here; duration, financing and roll-down are not modeled.
    """
    if "^IRX" not in prices:
        raise ValueError("rates carry requires ^IRX in prices")

    cfg = load_config()
    short = prices["^IRX"]["close"] / 100.0
    out: dict[str, pd.Series] = {}
    for asset in cfg.universe:
        if asset.asset_class != AssetClass.RATES or asset.role != "primary":
            continue
        if asset.ticker not in prices:
            continue
        long_y = prices[asset.ticker]["close"] / 100.0
        common = long_y.index.intersection(short.index)
        out[asset.label] = long_y.loc[common] - short.loc[common]

    return pd.DataFrame(out).sort_index()
