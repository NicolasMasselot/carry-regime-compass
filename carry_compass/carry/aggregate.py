import pandas as pd
from loguru import logger

from carry_compass.carry.commodity import compute_commodity_carry
from carry_compass.carry.credit import compute_credit_carry
from carry_compass.carry.equity import compute_equity_carry
from carry_compass.carry.fx import compute_fx_carry
from carry_compass.carry.rates import compute_rates_carry


def compute_all_carries(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Aggregate asset-class carry estimates into one date x asset-label frame.

    Args:
        prices: Mapping of Yahoo ticker to canonical OHLCV frames.

    Returns:
        Wide frame indexed by date with annualized decimal carry columns.

    Notes:
        Components with missing required legs are skipped with a warning so the
        dashboard can degrade gracefully instead of crashing on one bad ticker.
    """
    calculators = {
        "fx_carry": compute_fx_carry,
        "rates": compute_rates_carry,
        "credit": compute_credit_carry,
        "equity": compute_equity_carry,
        "commodity": compute_commodity_carry,
    }
    parts: list[pd.DataFrame] = []
    for asset_class, calculator in calculators.items():
        try:
            part = calculator(prices)
        except ValueError as exc:
            logger.warning("skipping {} carry: {}", asset_class, exc)
            continue
        if not part.empty:
            parts.append(part)

    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, axis=1).sort_index()
