from carry_compass.data.batch import fetch_universe
from carry_compass.vol.panel import PANEL_COLS, build_carry_vol_panel


def test_build_carry_vol_panel_integration() -> None:
    results = fetch_universe()
    prices = {ticker: result.df for ticker, result in results.items()}

    panel = build_carry_vol_panel(prices)

    assert list(panel.columns) == PANEL_COLS
    assert len(panel) > 0
    assert panel["asset_class"].notna().all()
    assert (panel["vol"] > 0).all()
    assert (panel["ratio"].abs() < 20).all()
    assert panel["asset_class"].nunique() == 5
