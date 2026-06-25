import json
from datetime import UTC, datetime
from pathlib import Path

from source.domain.entities import (
    Candle,
    DecisionVerdict,
    FundingOiSnapshot,
    GateResult,
    IndicatorSet,
    LiquidationEstimate,
    ProposedGridParams,
)
from source.domain.value_objects import Gate, GateStatus, GridType, Symbol, Trend, VerdictAction


FIXED_NOW = datetime(2026, 6, 1, tzinfo=UTC)

_FIXTURES_DIR = Path(__file__).parent / "pionex_responses"


def load_fixture(filename: str) -> dict:  # type: ignore[type-arg]
    return json.loads((_FIXTURES_DIR / filename).read_text())


def make_indicator_set(**overrides: object) -> IndicatorSet:
    defaults: dict[str, object] = {
        "interval": "4H",
        "as_of": FIXED_NOW,
        "adx14": 18.0,
        "atr14": 1_000.0,
        "atr_pct_of_price": 1.0,
        "sma50": 95_000.0,
        "macd": 200.0,
        "macd_signal": 150.0,
        "rsi14": 50.0,
        "last_price": 96_000.0,
        "swing_high_14d": 100_000.0,
        "swing_low_14d": 88_000.0,
        "realized_vol_1d": 0.02,
        "realized_vol_7d": 0.015,  # flat/falling — no rising-vol CAUTION by default
        "realized_vol_30d": 0.01,
    }
    return IndicatorSet(**(defaults | overrides))  # type: ignore[arg-type]


def make_funding_oi_snapshot(**overrides: object) -> FundingOiSnapshot:
    defaults: dict[str, object] = {
        "symbol": Symbol.BTC,
        "as_of": FIXED_NOW,
        "funding_rate_last": 0.0001,
        "open_interest": 5_000_000.0,
        "oi_pct_change_7d": 5.0,
    }
    return FundingOiSnapshot(**(defaults | overrides))  # type: ignore[arg-type]


def make_proposed_grid_params(**overrides: object) -> ProposedGridParams:
    defaults: dict[str, object] = {
        "symbol": Symbol.BTC,
        "trend": Trend.NEUTRAL,
        "grid_type": GridType.GEOMETRIC,
        "top": 100_000.0,
        "bottom": 88_000.0,
        "grid_levels": 50,
        "leverage": 3,
        "quote_investment": 1_000.0,
    }
    return ProposedGridParams(**(defaults | overrides))  # type: ignore[arg-type]


def make_liquidation_estimate(**overrides: object) -> LiquidationEstimate:
    proposal = overrides.pop("proposal", make_proposed_grid_params())  # type: ignore[assignment]
    defaults: dict[str, object] = {
        "proposal": proposal,
        "estimate_liquidation_price_up": None,
        "estimate_liquidation_price_down": None,
    }
    return LiquidationEstimate(**(defaults | overrides))  # type: ignore[arg-type]


def make_liquidation_estimate_with_buffers(
    buf_up: float | None,
    buf_down: float | None,
    proposal: ProposedGridParams | None = None,
) -> LiquidationEstimate:
    if proposal is None:
        proposal = make_proposed_grid_params()

    grid_range = proposal.top - proposal.bottom
    liq_up = proposal.top + buf_up * grid_range if buf_up is not None else None
    liq_down = proposal.bottom - buf_down * grid_range if buf_down is not None else None
    return LiquidationEstimate(
        proposal=proposal,
        estimate_liquidation_price_up=liq_up,
        estimate_liquidation_price_down=liq_down,
    )


def make_gate_result(
    gate: Gate = Gate.REGIME_RANGE_FIT,
    status: GateStatus = GateStatus.PASS,
    reasons: tuple[str, ...] = (),
    **raw_values: object,
) -> GateResult:
    return GateResult(gate=gate, status=status, reasons=reasons, raw_values=dict(raw_values))


def make_decision_verdict(**overrides: object) -> DecisionVerdict:
    gates = overrides.pop(
        "gates",
        (make_gate_result(Gate.REGIME_RANGE_FIT, GateStatus.PASS),),
    )
    defaults: dict[str, object] = {
        "symbol": Symbol.BTC,
        "as_of": FIXED_NOW,
        "action": VerdictAction.LAUNCH,
        "gates": gates,
        "notes": None,
    }
    return DecisionVerdict(**(defaults | overrides))  # type: ignore[arg-type]


def make_candle(time_ms: int, **overrides: object) -> Candle:
    defaults: dict[str, object] = {
        "time": datetime.fromtimestamp(time_ms / 1000, tz=UTC),
        "open": 95_000.0,
        "high": 96_000.0,
        "low": 94_000.0,
        "close": 95_500.0,
        "volume": 100.0,
    }
    return Candle(**(defaults | overrides))  # type: ignore[arg-type]


def make_candles(
    n: int,
    interval_minutes: int = 240,
    base_time_ms: int = 1_748_995_200_000,  # 2025-06-03 00:00 UTC
    base_close: float = 95_500.0,
) -> list[Candle]:
    candles = []
    for i in range(n):
        t_ms = base_time_ms + i * interval_minutes * 60 * 1000
        close = base_close + (i % 100) * 10.0
        candles.append(
            Candle(
                time=datetime.fromtimestamp(t_ms / 1000, tz=UTC),
                open=close - 200.0,
                high=close + 500.0,
                low=close - 600.0,
                close=close,
                volume=100.0 + i,
            )
        )
    return candles
