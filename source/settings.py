from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


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
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: SecretStr
    db_name: str = "grid_advisor"

    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    @property
    def connection_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


class MonitoringIntervals(BaseModel):
    health_check_minutes: int = 30
    auto_adjust_minutes: int = 30
    metrics_ttl_days: int = 90
    alert_debounce_minutes: int = 5


class MonitoringWeights(BaseModel):
    distance_to_liq: float = 0.35
    pnl: float = 0.20
    fill_ratio: float = 0.15
    volatility: float = 0.15
    funding: float = 0.10
    adx: float = 0.05


class MonitoringThresholds(BaseModel):
    liq_distance_green_min_pct: float = 15.0
    liq_distance_yellow_min_pct: float = 7.5

    pnl_green_min_pct: float = -5.0
    pnl_yellow_min_pct: float = -15.0

    fill_green_max: float = 0.70
    fill_yellow_max: float = 0.90

    atr_pct_green_max: float = 5.0
    atr_pct_yellow_max: float = 10.0

    funding_green_max_abs_pct: float = 15.0
    funding_yellow_max_abs_pct: float = 30.0

    adx_green_max: float = 25.0
    adx_yellow_max: float = 35.0

    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0


class MonitoringSettings(_BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MONITORING_", env_nested_delimiter="__")

    intervals: MonitoringIntervals = Field(default_factory=MonitoringIntervals)
    weights: MonitoringWeights = Field(default_factory=MonitoringWeights)
    thresholds: MonitoringThresholds = Field(default_factory=MonitoringThresholds)

    auto_adjust_enabled: bool = False
    auto_pause_on_red: bool = True
    auto_resume_on_green: bool = False
    max_consecutive_yellow_before_action: int = 4


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
    monitoring: MonitoringSettings = field(default_factory=MonitoringSettings)


@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    return Settings()
