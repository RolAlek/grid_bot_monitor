from datetime import UTC, datetime

from source.application.ports import NotifierPort
from source.application.services.decision_log_service import DecisionLogService
from source.application.services.gates.assess_liquidation_safety import AssessLiquidationSafetyService
from source.application.services.gates.assess_market_regime_first_gate import AssessMarketRegimeService
from source.application.services.gates.assess_positioning_second_gate import AssessPositioningService
from source.domain.entities import DecisionVerdict, GateResult, ProposedGridParams
from source.domain.value_objects import GateStatus, Symbol, VerdictAction
from source.settings import Settings


class RunWeeklyFullAssessment:
    def __init__(
        self,
        decision_service: DecisionLogService,
        gate1: AssessMarketRegimeService,
        gate2: AssessPositioningService,
        gate3: AssessLiquidationSafetyService,
        notifier: NotifierPort,
        settings: Settings,
    ) -> None:
        self._decision_service = decision_service
        self._gate1 = gate1
        self._gate2 = gate2
        self._gate3 = gate3
        self._notifier = notifier
        self._settings = settings

    async def run(self) -> DecisionVerdict:
        symbol = self._settings.pionex.symbol

        first_gate_result, proposal = await self._gate1.execute(symbol)
        gates: list[GateResult] = [first_gate_result]
        if first_gate_result.status != GateStatus.FAIL:
            second_gate_result = await self._gate2.execute(symbol)
            third_gate_result = await self._gate3.execute(proposal)
            gates.extend([second_gate_result, third_gate_result])

        verdict = self._resolve(
            symbol=symbol,
            gates=gates,
            proposal=proposal,
            notes="weekly full assessment",
        )

        await self._decision_service.persist_verdict(verdict)
        await self._notifier.send_digest(verdict)

        return verdict

    def _resolve(
        self,
        symbol: Symbol,
        gates: list[GateResult],
        notes: str | None,
        proposal: ProposedGridParams | None = None,
    ) -> DecisionVerdict:
        action = VerdictAction.LAUNCH

        if any(gate.status == GateStatus.FAIL for gate in gates):
            action = VerdictAction.HOLD

        elif any(gate.status == GateStatus.CAUTION for gate in gates):
            action = VerdictAction.REVIEW

        return DecisionVerdict(
            as_of=datetime.now(UTC),
            symbol=symbol,
            action=action,
            gates=tuple(gates),
            suggested_grid_top=proposal.top if proposal else None,
            suggested_grid_bottom=proposal.bottom if proposal else None,
            suggested_leverage=proposal.leverage if proposal else None,
            notes=notes,
        )
