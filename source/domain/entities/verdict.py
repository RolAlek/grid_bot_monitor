from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from source.constants import INSUFFICIENT_OI_HISTORY_REASON
from source.domain.entities.grid import ProposedGridParams
from source.domain.value_objects import Gate, GateStatus, Symbol, VerdictAction


@dataclass(frozen=True)
class GateResult:
    gate: Gate
    status: GateStatus
    reasons: tuple[str, ...]
    raw_values: dict[str, Any]


@dataclass(frozen=True)
class DecisionVerdict:
    symbol: Symbol
    action: VerdictAction
    gates: tuple[GateResult, ...]

    oid: UUID | None = None
    created_at: datetime | None = None
    notes: str | None = None

    # Suggested parameters
    suggested_parameters: ProposedGridParams | None = None

    @property
    def is_launchable_despite_review(self) -> bool:
        if self.action != VerdictAction.REVIEW:
            return False

        caution_gates = [gate for gate in self.gates if gate.status == GateStatus.CAUTION]

        if len(caution_gates) != 1:
            return False

        [caution_gate] = caution_gates

        if caution_gate.gate != Gate.POSITIONING:
            return False

        return caution_gate.reasons == (INSUFFICIENT_OI_HISTORY_REASON,)


@dataclass(frozen=True)
class GateRule:
    triggered: bool
    status: GateStatus
    message: str
