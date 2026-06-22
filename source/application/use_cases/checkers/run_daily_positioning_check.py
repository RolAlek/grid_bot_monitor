from datetime import UTC, datetime

from source.application.ports import MarketDataPort, NotifierPort
from source.application.services.decision_log_service import DecisionLogService
from source.application.services.oi_snapshot_service import OISnapshotService
from source.application.use_cases.assess_positioning import AssessPositioning
from source.application.use_cases.checkers.base import BaseChecker
from source.domain.entities import (
    DecisionVerdict,
    FundingOiSnapshot,
    Gate,
    GateResult,
    GateStatus,
    Symbol,
    VerdictAction,
)
from source.settings import Settings


ALERT_EMOJI = {"PASS": "🟢", "CAUTION": "🟡", "FAIL": "🔴"}
ALERT_TEMPLATE = (
    "{emoji} Gate status change — Positioning (Gate 2)\n"
    "Funding: {funding_rate:.1f}% annualized ({direction})\n"
    "OI 7d change: {oi_change}\n"
    "Previous: {prev_status} → Now: {current_status}\n"
    "No action taken — informational only."
)


class RunDailyPositioningCheck(BaseChecker):
    def __init__(
        self,
        market_data: MarketDataPort,
        gate2: AssessPositioning,
        oi_service: OISnapshotService,
        decision_service: DecisionLogService,
        notifier: NotifierPort,
        settings: Settings,
    ) -> None:
        super().__init__(market_data, gate2, oi_service)

        self._decision_service = decision_service
        self._notifier = notifier
        self._settings = settings

    async def run(self) -> GateResult:
        now = datetime.now(UTC)
        symbol = self._settings.pionex.symbol

        result, snapshot = await self.check_second_gate(symbol, now, is_save=True)

        await self._send_alert(symbol, snapshot, result)

        await self._decision_service.persist_verdict(
            DecisionVerdict(
                as_of=now,
                symbol=symbol,
                action=self._resolve_action(result.status),
                gates=(result,),
                suggested_grid_top=None,
                suggested_grid_bottom=None,
                suggested_leverage=None,
                notes="daily positioning check",
            )
        )

        return result

    async def _previous_gate2_status(self, symbol: Symbol) -> GateStatus | None:
        last = await self._decision_service.get_last_decision(symbol)
        if last is None:
            return None

        for gate in last.gates:
            if gate.gate == Gate.POSITIONING:
                return gate.status

        return None

    @staticmethod
    def _format_alert(
        snapshot: FundingOiSnapshot,
        result: GateResult,
        prev_status: GateStatus | None,
    ) -> str:
        direction = "long" if snapshot.funding_rate_annualized_pct > 0 else "short"
        oi_str = f"{snapshot.oi_pct_change_7d:.1f}%" if snapshot.oi_pct_change_7d else None
        prev_str = prev_status.name if prev_status else "NONE"
        emoji = ALERT_EMOJI.get(result.status.name, "⚪")

        return ALERT_TEMPLATE.format(
            emoji,
            snapshot.funding_rate_annualized_pct,
            direction,
            oi_str,
            prev_str,
            result.status.name,
        )

    @staticmethod
    def _resolve_action(status: GateStatus) -> VerdictAction:
        match status:
            case GateStatus.FAIL:
                return VerdictAction.HOLD
            case GateStatus.CAUTION:
                return VerdictAction.REVIEW
            case GateStatus.PASS:
                return VerdictAction.LAUNCH

    async def _send_alert(
        self,
        symbol: Symbol,
        snapshot: FundingOiSnapshot,
        result: GateResult,
    ) -> None:
        prev_status = await self._previous_gate2_status(symbol)

        if result.status != prev_status:
            alert = self._format_alert(snapshot, result, prev_status)
            await self._notifier.send_alert(alert)
