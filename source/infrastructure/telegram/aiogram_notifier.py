import html
from types import MappingProxyType
from typing import ClassVar

from aiogram import Bot

from source.application.ports import NotifierPort
from source.domain.entities import DecisionVerdict
from source.domain.value_objects import GateResult, GateStatus, VerdictAction
from source.presentation.bot.keyboards.inlines import build_verdict_reaction_kb


ALERT_TEMPLATE = (
    "{emoji} Gate status change — Positioning (Gate 2)\n\n"
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
        await self._bot.send_message(
            chat_id=self._chat_id,
            text=self._format_alert(result, prev_status),
            parse_mode="HTML",
        )

    async def send_digest(self, verdict: DecisionVerdict) -> None:
        if not verdict.oid:
            raise ValueError('"oid" is not set for decision verdict.')

        kb = build_verdict_reaction_kb(verdict.oid) if verdict.action == VerdictAction.LAUNCH else None

        await self._bot.send_message(
            chat_id=self._chat_id,
            text=self._format_digest(verdict),
            parse_mode="HTML",
            reply_markup=kb,
        )

    def _format_digest(self, verdict: DecisionVerdict) -> str:
        verdict_emoji = self._VERDICT_EMOJI.get(verdict.action, "⚪")
        symbol = html.escape(str(verdict.symbol))
        action = verdict.action.value.upper()

        sections = [f"{verdict_emoji} <b>Weekly Launch Assessment</b>\n\n<b>{symbol}</b> · Verdict: <b>{action}</b>"]

        gate_lines = []
        for gate in verdict.gates:
            gate_emoji = self._STATUS_EMOJI.get(gate.status, "⚪")
            gate_lines.append(f"{gate_emoji} <b>{gate.gate.name}</b> — {gate.status.name}")
            gate_lines.extend(f"   • {html.escape(reason)}" for reason in gate.reasons)

        if gate_lines:
            sections.append("\n".join(gate_lines))

        if verdict.action == VerdictAction.LAUNCH:
            param_lines: list[str] = [
                "🚀 Reply /confirm_launch to proceed — no order has been placed.\n\n",
                "🛠 <b>Launch parameters</b>:\n",
            ]

            if verdict.suggested_grid_top is not None and verdict.suggested_grid_bottom is not None:
                param_lines.append(
                    f"📐 <b>Range:</b> {verdict.suggested_grid_top:,.0f} - {verdict.suggested_grid_bottom:,.0f}\n"
                )
            if verdict.suggested_grid_levels is not None:
                param_lines.append(f"🔢 <b>Grid levels:</b> {verdict.suggested_grid_levels}\n")

            if verdict.suggested_grid_regime is not None:
                param_lines.append(f"📈 <b>Trend regime:</b> {verdict.suggested_grid_regime.value}\n")

            if verdict.suggested_grid_type is not None:
                param_lines.append(f"⚙️ <b>Grid type:</b> {verdict.suggested_grid_type.value}\n")

            if verdict.suggested_leverage is not None:
                param_lines.append(f"⚡️ <b>Leverage:</b> {verdict.suggested_leverage}x")

            sections.append("\n".join(param_lines))

        return "\n\n".join(sections)

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
