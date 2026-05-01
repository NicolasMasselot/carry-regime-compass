import numpy as np
import pandas as pd

from carry_compass.vol.realized import realized_vol


def test_realized_vol_constant_returns_zero() -> None:
    s = pd.Series([100.0] * 100, index=pd.bdate_range("2025-01-01", periods=100))

    v = realized_vol(s, window=30, min_obs=20)

    assert v.dropna().abs().max() < 1e-10


def test_realized_vol_known_value() -> None:
    rng = np.random.default_rng(42)
    rets = rng.normal(0, 0.01, size=500)
    px = 100 * np.exp(np.cumsum(rets))
    s = pd.Series(px, index=pd.bdate_range("2024-01-01", periods=500))

    v = realized_vol(s, window=30, min_obs=20).dropna()

    assert 0.13 < v.mean() < 0.19


def test_yield_vs_price_vol_branches() -> None:
    s = pd.Series(
        [2.0, 2.1, 2.05, 2.2, 2.15] * 30,
        index=pd.bdate_range("2025-01-01", periods=150),
    )

    v_price = realized_vol(s, window=30, is_yield=False).dropna()
    v_yield = realized_vol(s, window=30, is_yield=True).dropna()

    assert not np.isclose(v_price.iloc[-1], v_yield.iloc[-1])
