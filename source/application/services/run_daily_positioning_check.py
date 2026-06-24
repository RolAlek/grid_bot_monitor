from datetime import UTC, datetime

from source.application.ports import NotifierPort
from source.application.services.decision_log_service import DecisionLogService
from source.application.services.gates.assess_positioning_second_gate import AssessPositioningService
from source.domain.entities import DecisionVerdict, GateResult
from source.domain.value_objects import Gate, GateStatus, Symbol, VerdictAction
from source.settings import Settings


class RunDailyPositioningCheck:
    def __init__(
        self,
        second_gate: AssessPositioningService,
        decision_service: DecisionLogService,
        notifier: NotifierPort,
        settings: Settings,
    ) -> None:
        self._second_gate = second_gate
        self._decision_service = decision_service
        self._notifier = notifier
        self._settings = settings

    async def run(self) -> GateResult:
        symbol = self._settings.pionex.symbol
        second_gate_result = await self._second_gate.execute(symbol)

        await self._send_alert(symbol, second_gate_result)

        await self._decision_service.persist_verdict(
            DecisionVerdict(
                as_of=datetime.now(UTC),
                symbol=symbol,
                action=self._resolve_action(second_gate_result.status),
                gates=(second_gate_result,),
                suggested_grid_top=None,
                suggested_grid_bottom=None,
                suggested_leverage=None,
                notes="daily positioning check",
            )
        )

        return second_gate_result

    async def _send_alert(
        self,
        symbol: Symbol,
        result: GateResult,
    ) -> None:
        prev_status = await self._previous_gate2_status(symbol)

        if result.status != prev_status:
            await self._notifier.send_alert(result, prev_status)

    async def _previous_gate2_status(self, symbol: Symbol) -> GateStatus | None:
        last = await self._decision_service.get_last_decision(symbol)
        if last is None:
            return None

        for gate in last.gates:
            if gate.gate == Gate.POSITIONING:
                return gate.status

        return None

    @staticmethod
    def _resolve_action(status: GateStatus) -> VerdictAction:
        match status:
            case GateStatus.FAIL:
                return VerdictAction.HOLD
            case _:
                return VerdictAction.REVIEW  # CAUTION or PASS — daily check alone never confirms LAUNCH
