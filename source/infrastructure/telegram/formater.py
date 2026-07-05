import html
from types import MappingProxyType
from typing import ClassVar

from source.domain.entities import DecisionVerdict, GateResult, ProposedGridParams
from source.domain.entities.monitoring import Bot, ClassificationResult, HealthSnapshot
from source.domain.value_objects import AlertType, GateStatus, HealthStatus, VerdictAction


class TelegramMessageFormatter:
    _STATUS_EMOJI: ClassVar[MappingProxyType[GateStatus, str]] = MappingProxyType({
        GateStatus.PASS: "🟢",
        GateStatus.CAUTION: "🟡",
        GateStatus.FAIL: "🔴",
    })

    _VERDICT_EMOJI: ClassVar[MappingProxyType[VerdictAction, str]] = MappingProxyType({
        VerdictAction.LAUNCH: "🚀",
        VerdictAction.REVIEW: "⚠️",
        VerdictAction.HOLD: "⏸️",
    })

    _HEALTH_EMOJI: ClassVar[MappingProxyType[HealthStatus, str]] = MappingProxyType({
        HealthStatus.GREEN: "🟢",
        HealthStatus.YELLOW: "🟡",
        HealthStatus.RED: "🔴",
    })

    _ALERT_EMOJI: ClassVar[MappingProxyType[AlertType, str]] = MappingProxyType({
        AlertType.STATUS_CHANGE: "🔄",
        AlertType.LIQUIDATION_RISK: "💀",
        AlertType.GRID_DEPLETION: "📊",
        AlertType.HIGH_FUNDING: "💸",
        AlertType.VOLATILITY_SPIKE: "🌊",
        AlertType.PNL_DRAWDOWN: "📉",
        AlertType.API_ERROR: "⚡",
    })

    def format_digest(self, verdict: DecisionVerdict) -> str:
        sections = [
            (
                f"{self._VERDICT_EMOJI.get(verdict.action, '⚪')} <b>Weekly Launch Assessment</b>\n\n"
                f"<b>{html.escape(str(verdict.symbol))}</b>\n"
                f"⚖️ Verdict: <b>{verdict.action.value.upper()}</b>"
            )
        ]

        sections.append(self._aggregate_gate_lines(verdict.gates))

        if verdict.action == VerdictAction.LAUNCH and verdict.suggested_parameters:
            sections.append(self._aggregate_launch_parameters(verdict.suggested_parameters))

        return "\n\n".join(sections)

    def format_alert(
        self,
        result: GateResult,
        prev_status: GateStatus | None,
    ) -> str:
        funding = result.raw_values["funding_rate_annualized_pct"]
        oi_change = result.raw_values["oi_pct_change_7d"]

        oi_text = f"{oi_change:.1f}%" if oi_change is not None else "insufficient history"

        return (
            f"{self._STATUS_EMOJI.get(result.status, '⚪')} Gate status change — Positioning (Gate 2)\n\n"
            f"Funding: {funding:.1f}% annualized ({'long' if funding > 0 else 'short'})\n"
            f"Open Interest: {oi_text}\n"
            f"Previous: {prev_status.name if prev_status else 'NONE'} → Now: {result.status.name}\n\n"
            f"No action taken — informational only."
        )

    def _aggregate_gate_lines(self, gates: tuple[GateResult, ...]) -> str:
        gate_lines = ["<b>Gate Results</b>:"]

        for gate in gates:
            gate_lines.append(
                f"  {self._STATUS_EMOJI.get(gate.status, '⚪')} <b>{gate.gate.name}</b> — {gate.status.name}"
            )
            gate_lines.extend(f"   • {html.escape(reason)}" for reason in gate.reasons)

        return "\n".join(gate_lines)

    def _aggregate_launch_parameters(self, parameters: ProposedGridParams) -> str:
        return (
            f"🛠 <b>Launch parameters</b>:\n"
            f"  📐 <b>Range:</b> {parameters.top:,.0f} - {parameters.bottom:,.0f}\n"
            f"  🔢 <b>Number of grids:</b> {parameters.grid_levels}\n"
            f"  📈 <b>Trend regime:</b> {parameters.trend.value}\n"
            f"  ⚙️ <b>Grid mode:</b> {parameters.grid_type.value}\n"
            f"  ⚡️ <b>Leverage:</b> {parameters.leverage}x\n"
            f"  ⛔️ <b>Stop-loss</b> {parameters.stop_loss or 'Not specified'}\n"
            f"  💰 <b>Take-profit</b> {parameters.take_profit or 'Not specified'}\n"
        )

    def format_status_all(self, bots: list[Bot]) -> str:
        if not bots:
            return "🤖 <b>No active bots</b> — nothing to monitor."

        lines = ["🤖 <b>Active Bots Overview</b>\n"]
        for bot in bots:
            pnl_str = f"{bot.current_pnl_pct:+.1f}%" if bot.current_pnl_pct is not None else "—"
            fill_str = f"{bot.grid_fill_ratio * 100:.0f}%" if bot.grid_fill_ratio is not None else "—"
            liq_str = f"{bot.distance_to_liquidation_pct:.1f}%" if bot.distance_to_liquidation_pct is not None else "—"
            paused = " ⏸️" if bot.paused_by_monitor else ""

            lines.append(
                f"{self._HEALTH_EMOJI.get(bot.health_status, '⚪')} <b>{html.escape(str(bot.symbol))}</b>{paused}\n"
                f"  PnL: {pnl_str}  ·  Fill: {fill_str}  ·  Liq dist: {liq_str}"
            )

        return "\n".join(lines)

    def format_status_detail(self, bot: Bot, snapshot: HealthSnapshot) -> str:
        emoji = self._HEALTH_EMOJI.get(bot.health_status, "⚪")

        lines = [
            f"{emoji} <b>{html.escape(str(bot.symbol))}</b> — {bot.health_status.value.upper()}",
            f"🏥 Health Score: <b>{snapshot.health_score * 100:.0f}%</b>",
            "",
            "<b>📈 Market Indicators</b>",
            f"  Last Price: {snapshot.last_price:,.0f}",
            f"  ADX(14): {snapshot.adx14:.1f}",
            f"  ATR(14): {snapshot.atr14:,.0f} ({snapshot.atr_pct_of_price:.1f}% of price)",
            f"  RSI(14): {snapshot.rsi14:.1f}",
            f"  1d Vol: {snapshot.realized_vol_1d * 100:.1f}%  7d Vol: {snapshot.realized_vol_7d * 100:.1f}%",
            "",
            "<b>💰 Position</b>",
            f"  Unrealized PnL: {snapshot.unrealized_pnl:+,.2f}",
            (
                f"  Unrealized PnL %: {snapshot.unrealized_pnl_pct:+.1f}%"
                if snapshot.unrealized_pnl_pct is not None
                else "  Unrealized PnL %: —"
            ),
            (
                f"  Grid Fill: {snapshot.grid_fill_ratio * 100:.0f}%"
                f" ({snapshot.matched_orders}/{snapshot.total_orders} orders)"
            ),
            "",
            "<b>⚠️ Risk</b>",
            f"  Distance to Liquidation: {snapshot.distance_to_liquidation_pct:.1f}%",
            (
                f"  Liquidation Price: {snapshot.liquidation_price:,.0f}"
                if snapshot.liquidation_price is not None
                else "  Liquidation Price: —"
            ),
            f"  Leverage: {snapshot.leverage}x",
            "",
            "<b>💸 Funding</b>",
            f"  Funding Rate: {snapshot.funding_rate * 100:.4f}%",
            f"  Annualized: {snapshot.funding_rate_annualized_pct:.1f}%",
        ]

        if snapshot.triggered_alerts:
            alert_lines = ["", "<b>🚨 Triggered Alerts</b>"]
            for alert_type_str in snapshot.triggered_alerts:
                try:
                    alert_type = AlertType(alert_type_str)
                    alert_emoji = self._ALERT_EMOJI.get(alert_type, "⚪")
                    alert_lines.append(f"  {alert_emoji} {alert_type.value}")
                except ValueError:
                    alert_lines.append(f"  ⚪ {alert_type_str}")
            lines.extend(alert_lines)

        return "\n".join(lines)

    def format_health_alert(
        self,
        bot: Bot,
        previous_status: HealthStatus,
        result: ClassificationResult,
    ) -> str:
        prev_emoji = self._HEALTH_EMOJI.get(previous_status, "⚪")
        new_emoji = self._HEALTH_EMOJI.get(result.status, "⚪")
        score_pct = result.score * 100

        lines = [
            f"{new_emoji} <b>Health Status Change</b>",
            f"📊 <b>{html.escape(str(bot.symbol))}</b>",
            f"{prev_emoji} {previous_status.value.upper()} → {new_emoji} <b>{result.status.value.upper()}</b>",
            f"🏥 Health Score: <b>{score_pct:.0f}%</b>",
        ]

        if result.alerts:
            lines.extend(("", "<b>🚨 Triggers</b>"))
            for alert_type in result.alerts:
                alert_emoji = self._ALERT_EMOJI.get(alert_type, "⚪")
                lines.append(f"  {alert_emoji} {alert_type.value}")

        if result.details:
            lines.extend(("", "<b>📋 Metric Details</b>"))
            for key, value in result.details.items():
                label = key.replace("_", " ").title()
                if isinstance(value, float):
                    lines.append(f"  • {label}: {value:.2f}")
                else:
                    lines.append(f"  • {label}: {value}")

        return "\n".join(lines)

    def format_reconfigure_proposal(
        self,
        params: ProposedGridParams,
        gate_results: list[GateResult],
    ) -> str:
        sections = [
            "🔄 <b>Reconfigure Proposal</b>\n",
            self._aggregate_launch_parameters(params),
            "",
            self._aggregate_gate_lines(tuple(gate_results)),
        ]
        return "\n".join(sections)
