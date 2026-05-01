import pandas as pd
import pytest

from carry_compass.regime.centroid import compute_centroid


def test_centroid_median_then_time_series_z_score() -> None:
    dates = pd.bdate_range("2025-01-01", periods=30)
    rows = []
    for i, date in enumerate(dates):
        vol = 0.10 if i != 15 else 0.20
        for asset_idx in range(5):
            rows.append(
                {
                    "date": date,
                    "asset": f"asset_{asset_idx}",
                    "asset_class": "fx_carry",
                    "carry": 0.05,
                    "vol": vol,
                    "ratio": 0.5,
                }
            )

    centroid = compute_centroid(pd.DataFrame(rows))

    assert centroid["vol_z"].iloc[15] > 0
    assert centroid["vol_z"].drop(centroid.index[15]).mean() == pytest.approx(
        centroid["vol_z"].drop(centroid.index[15]).iloc[0]
    )
    assert centroid["n_assets"].iloc[15] == 5
