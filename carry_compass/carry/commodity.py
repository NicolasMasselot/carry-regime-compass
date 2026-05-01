import numpy as np
import pandas as pd


def compute_commodity_carry(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute commodity carry proxies from Yahoo futures and rates.

    Args:
        prices: Mapping containing CL/BZ, GC/IRX and/or HG frames.

    Returns:
        Wide date x commodity-label frame of annualized decimal carry.

    Notes:
        WTI uses a bounded CL-Brent cross-grade proxy, gold uses negative 3M
        funding cost, and copper uses six-month momentum as a futures-curve proxy.
    """
    out: dict[str, pd.Series] = {}
    if "CL=F" in prices and "BZ=F" in prices:
        cl = prices["CL=F"]["close"]
        bz = prices["BZ=F"]["close"]
        common = cl.index.intersection(bz.index)
        out["WTI front"] = (((cl.loc[common] - bz.loc[common]) / cl.loc[common]) * 12.0).clip(
            -0.999, 0.999
        )
    if "GC=F" in prices and "^IRX" in prices:
        rf = prices["^IRX"]["close"] / 100.0
        common = prices["GC=F"].index.intersection(rf.index)
        out["Gold"] = -rf.reindex(common)
    if "HG=F" in prices:
        cu = prices["HG=F"]["close"]
        out["Copper"] = np.log(cu / cu.shift(126)) * 2.0

    return pd.DataFrame(out).sort_index()
