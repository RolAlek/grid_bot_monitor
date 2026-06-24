from types import MappingProxyType
from typing import ClassVar

from aiogram import Bot

from source.application.ports import NotifierPort
from source.domain.entities import DecisionVerdict, GateResult
from source.domain.value_objects import GateStatus, VerdictAction


ALERT_TEMPLATE = (
    "{emoji} Gate status change — Positioning (Gate 2)\n"
    "Funding: {funding_rate:.1f}% annualized ({direction})\n"
    "OI 7d change: {oi_change}\n"
    "Previous: {prev_status} → Now: {current_status}\n"
    "No action taken — informational only."
)


class AiogramNotifier(NotifierPort):
    _STATUS_EMOJI: ClassVar[MappingProxyType[GateStatus, str]] = MappingProxyType({
        GateStatus.PASS: "🟢",
        GateStatus.CAUTION: "🟡",
        GateStatus.FAIL: "🔴",
    })

    _VERDICT_EMOJI: ClassVar[MappingProxyType[VerdictAction, str]] = MappingProxyType({
        VerdictAction.LAUNCH: "🟢",
        VerdictAction.REVIEW: "🟡",
        VerdictAction.HOLD: "🔴",
    })

    def __init__(self, bot: Bot, chat_id: int | str) -> None:
        self._bot = bot
        self._chat_id = chat_id

    async def send_alert(self, result: GateResult, prev_status: GateStatus | None) -> None:
        await self._bot.send_message(chat_id=self._chat_id, text=self._format_alert(result, prev_status))

    async def send_digest(self, verdict: DecisionVerdict) -> None:
        await self._bot.send_message(chat_id=self._chat_id, text=self._format_digest(verdict))

    def _format_digest(self, verdict: DecisionVerdict) -> str:
        emoji = self._VERDICT_EMOJI.get(verdict.action, "⚪")

        lines = [
            f"{emoji} Weekly launch assessment — {verdict.symbol}. Verdict: {verdict.action.value.upper()}",
        ]

        for gate in verdict.gates:
            gate_emoji = self._STATUS_EMOJI.get(gate.status, "⚪")
            reason = gate.reasons[0] if gate.reasons else "ok"
            lines.append(f"Gate ({gate.gate.name}): {gate_emoji} {gate.status.name} — {reason}")

        top = verdict.suggested_grid_top
        bottom = verdict.suggested_grid_bottom
        leverage = verdict.suggested_leverage
        if top is not None and bottom is not None and leverage is not None:
            lines.append(f"Suggested range: {bottom:,.0f}-{top:,.0f} | Leverage: {leverage}x")

        if verdict.action == VerdictAction.LAUNCH:
            lines.append("Reply /confirm_launch to proceed — no order has been placed.")

        return "\n".join(lines)

    def _format_alert(
        self,
        result: GateResult,
        prev_status: GateStatus | None,
    ) -> str:
        funding = result.raw_values["funding_rate_annualized_pct"]
        oi_change = result.raw_values["oi_pct_change_7d"]

        direction = "long" if funding > 0 else "short"
        oi_str = f"{oi_change:.1f}%" if oi_change is not None else "insufficient history"
        prev_str = prev_status.name if prev_status is not None else "NONE"
        emoji = self._STATUS_EMOJI.get(result.status, "⚪")

        return ALERT_TEMPLATE.format(
            emoji=emoji,
            funding_rate=funding,
            direction=direction,
            oi_change=oi_str,
            prev_status=prev_str,
            current_status=result.status.name,
        )
