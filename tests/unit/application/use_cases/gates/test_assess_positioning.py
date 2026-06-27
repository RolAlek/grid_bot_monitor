import dataclasses

import pytest

from source.application.use_cases.check_positioning_rueles import build_positioning_checks
from source.application.utils import evaluate_checks
from source.constants import FUNDING_ANNUALIZATION_FACTOR
from source.domain.entities import FundingOiSnapshot
from source.domain.value_objects import GateStatus
from source.settings import DecisionEngineSettings


def _status(snapshot: FundingOiSnapshot, settings: DecisionEngineSettings) -> GateStatus:
    return evaluate_checks(build_positioning_checks(snapshot, settings))[0]


def _reasons(snapshot: FundingOiSnapshot, settings: DecisionEngineSettings) -> tuple[str, ...]:
    return evaluate_checks(build_positioning_checks(snapshot, settings))[1]


def _snap_with_funding(base_sn: FundingOiSnapshot, annualized_pct: float, oi_change: float = 5.0) -> FundingOiSnapshot:
    rate_last = annualized_pct / FUNDING_ANNUALIZATION_FACTOR
    return dataclasses.replace(base_sn, funding_rate_last=rate_last, oi_pct_change_7d=oi_change)


@pytest.mark.parametrize(
    ("annualized_pct", "expected"),
    [
        (0.0, GateStatus.PASS),
        (19.9, GateStatus.PASS),
        (20.1, GateStatus.CAUTION),
        (39.9, GateStatus.CAUTION),
        (40.1, GateStatus.FAIL),
        (-20.1, GateStatus.CAUTION),
        (-40.1, GateStatus.FAIL),
    ],
)
def test_funding_rate_boundaries(
    base_snapshot: FundingOiSnapshot,
    settings: DecisionEngineSettings,
    annualized_pct: float,
    expected: GateStatus,
) -> None:
    snapshot = _snap_with_funding(base_snapshot, annualized_pct)
    assert _status(snapshot, settings) == expected, f"funding={annualized_pct}%"


def test_oi_change_none_is_caution_not_pass(
    base_snapshot: FundingOiSnapshot,
    settings: DecisionEngineSettings,
) -> None:
    snapshot = dataclasses.replace(base_snapshot, oi_pct_change_7d=None)
    assert _status(snapshot, settings) == GateStatus.CAUTION
    reasons = _reasons(snapshot, settings)
    assert any(
        "history" in reason.lower() or "7 days" in reason.lower() or "Insufficient" in reason for reason in reasons
    )


def test_crowded_long_fails(
    base_snapshot: FundingOiSnapshot,
    settings: DecisionEngineSettings,
) -> None:
    # funding=25% (> caution_pct=20), oi_change=21% (> fail_pct=20) → crowded long FAIL
    snapshot = _snap_with_funding(base_snapshot, 25.0, oi_change=21.0)
    assert _status(snapshot, settings) == GateStatus.FAIL
    reasons = _reasons(snapshot, settings)
    assert any("long" in reason.lower() or "Crowded" in reason for reason in reasons)


def test_crowded_short_fails(
    base_snapshot: FundingOiSnapshot,
    settings: DecisionEngineSettings,
) -> None:
    snapshot = _snap_with_funding(base_snapshot, -25.0, oi_change=21.0)
    assert _status(snapshot, settings) == GateStatus.FAIL
    reasons = _reasons(snapshot, settings)
    assert any("short" in reason.lower() or "Crowded" in reason for reason in reasons)


def test_crowded_long_below_fail_oi_threshold_is_caution(
    base_snapshot: FundingOiSnapshot,
    settings: DecisionEngineSettings,
) -> None:
    # funding=25% (in caution zone), oi_change=15% (< fail 20%) → only funding CAUTION
    snapshot = _snap_with_funding(base_snapshot, 25.0, oi_change=15.0)
    assert _status(snapshot, settings) == GateStatus.CAUTION


def test_funding_at_fail_threshold_is_always_fail(
    base_snapshot: FundingOiSnapshot,
    settings: DecisionEngineSettings,
) -> None:
    snapshot = _snap_with_funding(base_snapshot, 45.0, oi_change=0.0)
    assert _status(snapshot, settings) == GateStatus.FAIL
