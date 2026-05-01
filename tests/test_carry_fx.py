import pytest

from carry_compass.carry.fx import compute_fx_carry
from tests.conftest import make_price_frame


def test_fx_carry_uses_em_sign_flip_and_standard_pair_direction() -> None:
    prices = {
        "USDBRL=X": make_price_frame(5.0, periods=5),
        "AUDJPY=X": make_price_frame(95.0, periods=5),
    }

    result = compute_fx_carry(prices)

    assert result["USD/BRL"].iloc[-1] == pytest.approx(0.0675)
    assert result["AUD/JPY"].iloc[-1] == pytest.approx(0.036)
