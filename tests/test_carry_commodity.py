import pytest

from carry_compass.carry.commodity import compute_commodity_carry
from tests.conftest import make_price_frame


def test_commodity_carry_wti_cross_grade_proxy() -> None:
    result = compute_commodity_carry({"CL=F": make_price_frame(80.0), "BZ=F": make_price_frame(84.0)})

    assert result["WTI front"].iloc[-1] == pytest.approx(-0.6)
