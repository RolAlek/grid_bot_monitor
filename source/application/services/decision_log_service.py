import json
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import asdict

from source.application.dto import DecisionLogCreateDTO
from source.domain.value_objects import DecisionVerdict, GateResult, Symbol, VerdictAction
from source.infrastructure.database.repositories.decision_repository import DecisionLogRepository


class DecisionLogService:
    def __init__(
        self,
        provider_decision_log_repository: Callable[[], AbstractAsyncContextManager[DecisionLogRepository]],
    ) -> None:
        self._provider_decision_log_repository = provider_decision_log_repository

    async def persist_verdict(self, verdict: DecisionVerdict) -> None:

        async with self._provider_decision_log_repository() as repository:
            await repository.add(
                DecisionLogCreateDTO(
                    symbol=verdict.symbol,
                    action=verdict.action,
                    gates_json=json.dumps([asdict(gate) for gate in verdict.gates]),
                    notes=verdict.notes,
                )
            )

    async def get_last_decision(self, symbol: Symbol) -> DecisionVerdict | None:
        async with self._provider_decision_log_repository() as repository:
            decision = await repository.get_last_decision(symbol)

        if not decision:
            return None

        gates = [
            GateResult(
                gate=gate["gate"],
                status=gate["status"],
                reasons=gate["reasons"],
                raw_values=gate["raw_values"],
            )
            for gate in json.loads(decision.gates_json)
        ]

        return DecisionVerdict(
            symbol=Symbol(decision.symbol),
            as_of=decision.created_at,
            action=VerdictAction(decision.action),
            gates=gates,
            suggested_grid_top=None,
            suggested_grid_bottom=None,
            suggested_leverage=None,
            notes=decision.notes,
        )
