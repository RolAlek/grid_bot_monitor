from dataclasses import dataclass
from datetime import datetime
from typing import Any

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

    oid: str | None = None
    created_at: datetime | None = None
    notes: str | None = None

    # Suggested parameters
    suggested_parameters: ProposedGridParams | None = None


@dataclass(frozen=True)
class GateRule:
    triggered: bool
    status: GateStatus
    message: str
