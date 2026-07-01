import html
from types import MappingProxyType
from typing import ClassVar

from source.domain.entities import DecisionVerdict, GateResult, ProposedGridParams
from source.domain.value_objects import GateStatus, VerdictAction


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

        return (
            f"{self._STATUS_EMOJI.get(result.status, '⚪')} Gate status change — Positioning (Gate 2)\n\n"
            f"Funding: {funding:.1f}% annualized ({'long' if funding > 0 else 'short'})\n"
            f"Open Interest: {oi_change:.1f}% (7d change: {oi_change:.1f}%)\n"
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
