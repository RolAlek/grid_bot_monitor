from dataclasses import dataclass, field
from functools import lru_cache

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from source.domain.value_objects import Symbol


class _BaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


class PionexSettings(_BaseSettings):
    base_url: HttpUrl = HttpUrl("https://api.pionex.com")
    api_key: str | None = None
    api_secret: str | None = None

    symbol: Symbol = Symbol.BTC
    kline_interval: str = "4H"
    limit: int = 500

    @property
    def connection_url(self):
        return self.base_url.encoded_string()


class DecisionEngineSettings(_BaseSettings):
    adx_pass_max: float = 25.0
    adx_caution_max: float = 30.0
    atr_range_multiplier_min: float = 3.0

    funding_annualized_caution_pct: float = 20.0
    funding_annualized_fail_pct: float = 40.0
    oi_7d_change_caution_pct: float = 10.0
    oi_7d_change_fail_pct: float = 20.0
    vol_term_structure_min_ratio: float = 1.05

    liq_buffer_multiplier_min: float = 2.5
    leverage_hard_cap: int = 5

    # Default grid parameters used when auto-drawing a proposal from swing range
    default_grid_rows: int = 50
    default_leverage: int = 3
    default_quote_investment: float = 1_000.0


@dataclass(frozen=True)
class Settings:
    pionex: PionexSettings = field(default_factory=PionexSettings)
    decision_engine: DecisionEngineSettings = field(
        default_factory=DecisionEngineSettings
    )


@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    return Settings()
