from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from source.domain.entities import GateResult, ProposedGridParams
from source.domain.entities.monitoring import Bot, ClassificationResult, HealthSnapshot
from source.domain.value_objects import AlertType, Gate, GateStatus, GridType, HealthStatus, Symbol, Trend
from source.infrastructure.telegram.aiogram_notifier import AiogramNotifier
from source.infrastructure.telegram.formater import TelegramMessageFormatter


def _make_bot(
    *,
    symbol: Symbol = Symbol.BTC,
    health_status: HealthStatus = HealthStatus.GREEN,
    current_pnl_pct: float | None = 2.5,
    grid_fill_ratio: float | None = 0.45,
    distance_to_liquidation_pct: float | None = 25.0,
    paused: bool = False,
) -> Bot:
    return Bot(
        symbol=symbol,
        oid=uuid4(),
        health_status=health_status,
        current_pnl_pct=current_pnl_pct,
        grid_fill_ratio=grid_fill_ratio,
        distance_to_liquidation_pct=distance_to_liquidation_pct,
        paused_by_monitor=paused,
    )


def _make_snapshot(
    *,
    symbol: Symbol = Symbol.BTC,
    health_status: HealthStatus = HealthStatus.GREEN,
    health_score: float = 0.85,
    triggered_alerts: tuple[str, ...] = (),
) -> HealthSnapshot:
    return HealthSnapshot(
        grid_launch_oid=uuid4(),
        symbol=symbol,
        last_price=96_000.0,
        leverage=3,
        adx14=20.0,
        atr14=1_000.0,
        atr_pct_of_price=1.0,
        rsi14=55.0,
        realized_vol_1d=0.02,
        realized_vol_7d=0.015,
        unrealized_pnl=150.0,
        unrealized_pnl_pct=2.5,
        grid_fill_ratio=0.45,
        distance_to_liquidation_pct=25.0,
        liquidation_price=72_000.0,
        funding_rate=0.0001,
        funding_rate_annualized_pct=5.0,
        matched_orders=23,
        total_orders=50,
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
        health_status=health_status,
        health_score=health_score,
        triggered_alerts=triggered_alerts,
    )


def _make_classification(*, status: HealthStatus = HealthStatus.YELLOW, score: float = 0.65) -> ClassificationResult:
    return ClassificationResult(
        status=status,
        score=score,
        alerts=(AlertType.VOLATILITY_SPIKE, AlertType.GRID_DEPLETION),
        details={"atr_pct_of_price": 8.5, "grid_fill_ratio": 0.78},
    )


def _make_proposal() -> ProposedGridParams:
    return ProposedGridParams(
        symbol=Symbol.BTC,
        top=100_000.0,
        bottom=88_000.0,
        grid_levels=50,
        leverage=3,
        quote_investment=1_000.0,
        trend=Trend.NEUTRAL,
        grid_type=GridType.GEOMETRIC,
        last_price=96_000.0,
    )


def _make_gate_results() -> list[GateResult]:
    return [
        GateResult(
            gate=Gate.REGIME_RANGE_FIT,
            status=GateStatus.PASS,
            reasons=("adx within range",),
            raw_values={"adx14": 20.0},
        ),
        GateResult(
            gate=Gate.POSITIONING,
            status=GateStatus.CAUTION,
            reasons=("high funding",),
            raw_values={"funding_rate_annualized_pct": 25.0},
        ),
    ]


class TestFormatStatusAll:
    def test_empty_list_returns_no_bots_message(self) -> None:
        fmt = TelegramMessageFormatter()
        result = fmt.format_status_all([])
        assert "No active bots" in result

    def test_single_green_bot(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot()
        result = fmt.format_status_all([bot])

        assert "BTC_USDT_PERP" in result
        assert "🟢" in result
        assert "+2.5%" in result
        assert "45%" in result
        assert "25.0%" in result

    def test_paused_bot_shows_indicator(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot(paused=True)
        result = fmt.format_status_all([bot])

        assert "⏸️" in result

    def test_multiple_bots_with_different_statuses(self) -> None:
        fmt = TelegramMessageFormatter()
        green = _make_bot(symbol=Symbol.BTC, health_status=HealthStatus.GREEN)
        red = _make_bot(symbol=Symbol.ETH, health_status=HealthStatus.RED, current_pnl_pct=-18.0)
        result = fmt.format_status_all([green, red])

        assert "BTC_USDT_PERP" in result
        assert "ETH_USDT_PERP" in result
        assert "🟢" in result
        assert "🔴" in result
        assert "-18.0%" in result

    def test_none_metrics_show_dash(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot(current_pnl_pct=None, grid_fill_ratio=None, distance_to_liquidation_pct=None)
        result = fmt.format_status_all([bot])

        assert "—" in result


class TestFormatStatusDetail:
    def test_includes_all_sections(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot()
        snapshot = _make_snapshot()
        result = fmt.format_status_detail(bot, snapshot)

        assert "BTC_USDT_PERP" in result
        assert "GREEN" in result
        assert "85%" in result  # health score
        assert "Market Indicators" in result
        assert "Position" in result
        assert "Risk" in result
        assert "Funding" in result

    def test_shows_triggered_alerts(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot(health_status=HealthStatus.RED)
        snapshot = _make_snapshot(
            health_status=HealthStatus.RED,
            health_score=0.30,
            triggered_alerts=("volatility_spike", "liquidation_risk"),
        )
        result = fmt.format_status_detail(bot, snapshot)

        assert "Triggered Alerts" in result
        assert "volatility_spike" in result
        assert "liquidation_risk" in result

    def test_unknown_alert_type_handled(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot()
        snapshot = _make_snapshot(triggered_alerts=("unknown_type",))
        result = fmt.format_status_detail(bot, snapshot)

        assert "unknown_type" in result


class TestFormatHealthAlert:
    def test_status_transition_displayed(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot()
        result = fmt.format_health_alert(bot, HealthStatus.GREEN, _make_classification(status=HealthStatus.RED))

        assert "GREEN →" in result or "GREEN" in result
        assert "RED" in result
        assert "Health Status Change" in result

    def test_alerts_listed(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot()
        result = fmt.format_health_alert(bot, HealthStatus.GREEN, _make_classification())

        assert "Triggers" in result
        assert "volatility_spike" in result
        assert "grid_depletion" in result

    def test_details_included(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot()
        result = fmt.format_health_alert(bot, HealthStatus.GREEN, _make_classification())

        assert "Metric Details" in result
        assert "8.50" in result  # atr_pct
        assert "0.78" in result  # grid_fill_ratio

    def test_health_score_percentage(self) -> None:
        fmt = TelegramMessageFormatter()
        bot = _make_bot()
        result = fmt.format_health_alert(bot, HealthStatus.GREEN, _make_classification(score=0.65))

        assert "65%" in result


class TestFormatReconfigureProposal:
    def test_includes_parameters_and_gates(self) -> None:
        fmt = TelegramMessageFormatter()
        params = _make_proposal()
        gates = _make_gate_results()
        result = fmt.format_reconfigure_proposal(params, gates)

        assert "Reconfigure Proposal" in result
        assert "100,000" in result
        assert "88,000" in result
        assert "50" in result  # grid_levels

    def test_includes_gate_results(self) -> None:
        fmt = TelegramMessageFormatter()
        params = _make_proposal()
        gates = _make_gate_results()
        result = fmt.format_reconfigure_proposal(params, gates)

        assert "Gate Results" in result
        assert "REGIME_RANGE_FIT" in result
        assert "POSITIONING" in result


class TestSendHealthAlert:
    async def test_send_health_alert_formats_and_sends(self) -> None:
        send_msg = AsyncMock()
        bot_mock = AsyncMock()
        bot_mock.send_message = send_msg
        notifier = AiogramNotifier(bot=bot_mock, chat_id=123)

        bot = _make_bot(health_status=HealthStatus.RED)
        classification = _make_classification(status=HealthStatus.RED)
        await notifier.send_health_alert(bot, HealthStatus.GREEN, classification)

        send_msg.assert_called_once()
        text: str = send_msg.call_args.kwargs["text"]
        assert "Health Status Change" in text
        assert "GREEN" in text
        assert "RED" in text
        assert send_msg.call_args.kwargs["parse_mode"] == "HTML"
        # Keyboard is built and attached
        kb = send_msg.call_args.kwargs.get("reply_markup")
        assert kb is not None

    async def test_send_health_alert_includes_triggers_in_text(self) -> None:
        send_msg = AsyncMock()
        bot_mock = AsyncMock()
        bot_mock.send_message = send_msg
        notifier = AiogramNotifier(bot=bot_mock, chat_id=456)

        bot = _make_bot()
        classification = _make_classification(status=HealthStatus.YELLOW)
        await notifier.send_health_alert(bot, HealthStatus.GREEN, classification)

        text: str = send_msg.call_args.kwargs["text"]
        assert "volatility_spike" in text
        assert "grid_depletion" in text
        # Keyboard is attached
        kb = send_msg.call_args.kwargs.get("reply_markup")
        assert kb is not None
