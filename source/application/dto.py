from abc import ABC
from dataclasses import dataclass
from datetime import datetime

from source.domain.value_objects import Symbol, VerdictAction


@dataclass(frozen=True, slots=True)
class AbstractCreateDTO(ABC):
    pass


@dataclass(frozen=True, slots=True)
class OISnapshotDTO(AbstractCreateDTO):
    symbol: Symbol
    open_interests: float


@dataclass(frozen=True, slots=True)
class DecisionLogCreateDTO(AbstractCreateDTO):
    symbol: Symbol
    action: VerdictAction
    gates_json: str
    notes: str | None


@dataclass(frozen=True, slots=True)
class DecisionLogGetDTO(AbstractCreateDTO):
    symbol: Symbol
    action: VerdictAction
    gates_json: str
    notes: str | None
    created_at: datetime
