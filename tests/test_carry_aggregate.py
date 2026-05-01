from carry_compass.carry.aggregate import compute_all_carries
from tests.conftest import make_price_frame


def test_aggregate_skips_missing_required_legs() -> None:
    prices = {"USDMXN=X": make_price_frame(18.0, periods=30)}

    carries = compute_all_carries(prices)

    assert list(carries.columns) == ["USD/MXN"]
    assert not carries.empty
