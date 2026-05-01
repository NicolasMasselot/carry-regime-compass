import pytest

from carry_compass.carry.credit import compute_credit_carry
from tests.conftest import make_price_frame


def test_credit_carry_uses_distribution_yield_minus_ief(mocker) -> None:
    mocker.patch(
        "carry_compass.carry.credit._ticker_dividend_yield",
        side_effect=lambda ticker, fallback: {"HYG": 0.065, "IEF": 0.040}[ticker],
    )

    result = compute_credit_carry({"HYG": make_price_frame(80.0), "IEF": make_price_frame(95.0)})

    assert result["HY ETF"].iloc[-1] == pytest.approx(0.025)
