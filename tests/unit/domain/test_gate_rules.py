import pytest

from source.application.utils import evaluate_checks
from source.domain.value_objects import GateRule, GateStatus


def _rule(triggered: bool, status: GateStatus, message: str = "") -> GateRule:
    return GateRule(triggered=triggered, status=status, message=message)


@pytest.mark.parametrize(
    ("rules", "expected"),
    [
        # Single PASS
        ([_rule(True, GateStatus.PASS)], GateStatus.PASS),
        # PASS + FAIL → FAIL (the regression case)
        ([_rule(True, GateStatus.PASS), _rule(True, GateStatus.FAIL)], GateStatus.FAIL),
        # PASS + CAUTION → CAUTION
        ([_rule(True, GateStatus.PASS), _rule(True, GateStatus.CAUTION)], GateStatus.CAUTION),
        # All three — FAIL wins
        (
            [_rule(True, GateStatus.PASS), _rule(True, GateStatus.CAUTION), _rule(True, GateStatus.FAIL)],
            GateStatus.FAIL,
        ),
        # Order shouldn't matter — FAIL still wins
        ([_rule(True, GateStatus.FAIL), _rule(True, GateStatus.CAUTION)], GateStatus.FAIL),
        (
            [_rule(True, GateStatus.CAUTION), _rule(True, GateStatus.FAIL), _rule(True, GateStatus.PASS)],
            GateStatus.FAIL,
        ),
    ],
)
def test_severity_ordering(rules: list[GateRule], expected: GateStatus) -> None:
    status, _ = evaluate_checks(rules)
    assert status == expected


def test_untriggered_checks_do_not_contribute() -> None:
    rules = [
        _rule(False, GateStatus.FAIL, "should not appear"),
        _rule(True, GateStatus.CAUTION, "should appear"),
    ]
    status, reasons = evaluate_checks(rules)
    assert status == GateStatus.CAUTION
    assert reasons == ("should appear",)


def test_empty_checks_return_pass() -> None:
    status, reasons = evaluate_checks([])
    assert status == GateStatus.PASS
    assert reasons == ()


def test_only_triggered_reasons_included() -> None:
    rules = [
        _rule(True, GateStatus.CAUTION, "reason A"),
        _rule(False, GateStatus.FAIL, "reason B — suppressed"),
        _rule(True, GateStatus.PASS, "reason C"),
    ]
    _, reasons = evaluate_checks(rules)
    assert "reason A" in reasons
    assert "reason C" in reasons
    assert "reason B — suppressed" not in reasons


def test_all_untriggered_returns_pass() -> None:
    rules = [
        _rule(False, GateStatus.FAIL),
        _rule(False, GateStatus.CAUTION),
    ]
    status, reasons = evaluate_checks(rules)
    assert status == GateStatus.PASS
    assert reasons == ()
