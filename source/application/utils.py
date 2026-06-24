from source.domain.value_objects import GateRule, GateStatus


def evaluate_checks(checks: list[GateRule]) -> tuple[GateStatus, tuple[str, ...]]:
    statuses = [GateStatus.PASS] + [check.status for check in checks if check.triggered]
    reasons = [check.message for check in checks if check.triggered]

    return max(statuses), tuple(reasons)
