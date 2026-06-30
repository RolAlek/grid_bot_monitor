from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from source.domain.value_objects import Symbol


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class _BaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


class AppSettings(_BaseSettings):
    log_level: LogLevel = LogLevel.DEBUG
    log_json: bool = True
    log_dir: Path = Path("logs")
    log_file_days: int = 3

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.upper()
        return value


class PionexSettings(_BaseSettings):
    base_url: HttpUrl = HttpUrl("https://api.pionex.com")
    api_key: SecretStr
    api_secret: SecretStr
    timeout: float = 10

    symbol: Symbol = Symbol.BTC
    kline_interval: str = "4H"
    limit: int = 500

    @property
    def connection_url(self) -> str:
        return self.base_url.encoded_string()


class DecisionEngineSettings(_BaseSettings):
    adx_pass_max: float = 25.0
    adx_caution_max: float = 30.0
    atr_range_multiplier_min: float = 3.0
    target_cell_atr_fraction: float = 0.3

    funding_annualized_caution_pct: float = 20.0
    funding_annualized_fail_pct: float = 40.0
    oi_7d_change_caution_pct: float = 10.0
    oi_7d_change_fail_pct: float = 20.0
    vol_term_structure_min_ratio: float = 1.05

    trend_bias_long_threshold: int = 2
    trend_bias_short_threshold: int = -2

    liq_buffer_multiplier_min: float = 2.5
    leverage_hard_cap: int = 5

    # Default grid parameters used when auto-drawing a proposal from swing range
    default_leverage: int = 1
    default_quote_investment: float = 1_000.0
    min_grid_rows: int = 5
    max_grid_rows: int = 120

    take_profit_buffer_atr: float = 3.0


class DatabaseSettings(_BaseSettings):
    url: str = "sqlite+aiosqlite:///{}.db"
    name: str = "advisor"

    echo: bool = False

    @property
    def connection_url(self) -> str:
        return self.url.format(self.name)


class TelegramSettings(_BaseSettings):
    token: SecretStr
    chat_id: str


@dataclass(frozen=True)
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    pionex: PionexSettings = field(default_factory=PionexSettings)
    decision_engine: DecisionEngineSettings = field(default_factory=DecisionEngineSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    telegram: TelegramSettings = field(default_factory=TelegramSettings)


@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    return Settings()
