import pytest

from carry_compass.carry.equity import compute_equity_carry
from tests.conftest import make_price_frame


def test_equity_carry_uses_earnings_yield_minus_rf(mocker) -> None:
    mocker.patch("carry_compass.carry.equity._trailing_pe", return_value=20.0)

    result = compute_equity_carry({"^GSPC": make_price_frame(5000.0), "^IRX": make_price_frame(4.0)})

    assert result["S&P 500"].iloc[-1] == pytest.approx(0.01)
