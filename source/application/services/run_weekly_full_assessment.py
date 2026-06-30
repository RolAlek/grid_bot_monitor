from datetime import UTC, datetime

import structlog

from source.application.ports import NotifierPort
from source.application.services.decision_log_service import DecisionLogService
from source.application.services.gates.assess_liquidation_safety_third_gate import AssessLiquidationSafetyService
from source.application.services.gates.assess_market_regime_first_gate import AssessMarketRegimeService
from source.application.services.gates.assess_positioning_second_gate import AssessPositioningService
from source.domain.entities import DecisionVerdict, ProposedGridParams
from source.domain.value_objects import GateResult, GateStatus, Symbol, VerdictAction
from source.settings import Settings


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


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
        logger.info("Weekly full assessment started", symbol=symbol.value)

        first_gate_result, proposal = await self._gate1.execute(symbol)
        logger.info("Gate 1 result", gate=first_gate_result.gate.name, status=first_gate_result.status.name)
        gates: list[GateResult] = [first_gate_result]

        if first_gate_result.status != GateStatus.FAIL:
            second_gate_result = await self._gate2.execute(symbol)
            logger.info("Gate 2 result", gate=second_gate_result.gate.name, status=second_gate_result.status.name)

            third_gate_result = await self._gate3.execute(proposal)
            logger.info("Gate 3 result", gate=third_gate_result.gate.name, status=third_gate_result.status.name)

            gates.extend([second_gate_result, third_gate_result])

        verdict = self._resolve(
            symbol=symbol,
            gates=gates,
            proposal=proposal,
            notes="weekly full assessment",
        )

        logger.info("Verdict resolved", action=verdict.action.value)
        verdict = await self._decision_service.persist_verdict(verdict)
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
            notes=notes,
            suggested_parameters=proposal,
        )
