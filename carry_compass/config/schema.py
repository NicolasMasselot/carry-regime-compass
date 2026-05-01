from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AssetClass(str, Enum):
    """Supported asset-class buckets in the carry monitor."""

    FX_CARRY = "fx_carry"
    RATES = "rates"
    CREDIT = "credit"
    EQUITY = "equity"
    COMMODITY = "commodity"


class Asset(BaseModel):
    """One instrument entry from the configured Yahoo universe."""

    ticker: str
    label: str
    asset_class: AssetClass
    role: Literal["primary", "leg", "reference"] = "primary"
    pair_with: str | None = None


class CacheConfig(BaseModel):
    """Cache storage settings."""

    sqlite_path: Path = Path("data/cache/prices.db")
    parquet_dir: Path = Path("data/cache/parquet")
    ttl_minutes: int = 15


class FetchConfig(BaseModel):
    """Yahoo fetch behavior and retry settings."""

    history_days: int = 400
    request_timeout_s: float = 10.0
    max_retries: int = 3
    backoff_seconds: float = 2.0


class VolConfig(BaseModel):
    """Realized-volatility window and annualization settings."""

    window_days: int = 30
    annualization_factor: int = 252
    min_observations: int = 20


class RegimeThresholds(BaseModel):
    """Thresholds used by the carry/vol regime classifier."""

    risk_on_carry_z_min: float = 0.5
    risk_on_vol_z_max: float = -0.2
    deleveraging_vol_z_min: float = 1.0
    deleveraging_carry_z_max: float = -0.3
    transition_smoothing_days: int = 5


class AppConfig(BaseModel):
    """Validated application configuration loaded from YAML."""

    universe: list[Asset] = Field(min_length=1)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    fetch: FetchConfig = Field(default_factory=FetchConfig)
    vol: VolConfig = Field(default_factory=VolConfig)
    regime: RegimeThresholds = Field(default_factory=RegimeThresholds)
    refresh_seconds: int = 300

    @field_validator("universe")
    @classmethod
    def tickers_must_be_unique(cls, universe: list[Asset]) -> list[Asset]:
        """Validate that each Yahoo ticker appears once.

        Args:
            universe: Parsed list of configured assets.

        Returns:
            The unchanged universe if all tickers are unique.
        """
        tickers = [asset.ticker for asset in universe]
        duplicates = sorted({ticker for ticker in tickers if tickers.count(ticker) > 1})
        if duplicates:
            raise ValueError(f"duplicate tickers in universe: {', '.join(duplicates)}")
        return universe
