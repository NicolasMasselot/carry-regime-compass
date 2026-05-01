import pytest

from carry_compass.carry.rates import compute_rates_carry
from tests.conftest import make_price_frame


def _yield_frame(value: float):
    return make_price_frame(value, periods=10)


def test_rates_carry_is_long_yield_minus_3m_yield() -> None:
    result = compute_rates_carry({"^IRX": _yield_frame(2.0), "^TNX": _yield_frame(4.5)})

    assert result["US 10Y"].iloc[-1] == pytest.approx(0.025)


def test_rates_carry_requires_irx() -> None:
    with pytest.raises(ValueError, match="\\^IRX"):
        compute_rates_carry({"^TNX": _yield_frame(4.5)})
