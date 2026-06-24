from source.domain.entities import LiquidationEstimate
from source.domain.value_objects import GateRule, GateStatus, Trend
from source.settings import DecisionEngineSettings


def build_liquidation_safety_checks(
    estimate: LiquidationEstimate,
    settings: DecisionEngineSettings,
) -> list[GateRule]:
    proposal = estimate.proposal
    up, down = estimate.buffer_multiplier_up, estimate.buffer_multiplier_down

    return [
        GateRule(
            triggered=proposal.leverage > settings.leverage_hard_cap,
            status=GateStatus.FAIL,
            message=f"Leverage {proposal.leverage}x exceeds hard cap {settings.leverage_hard_cap}x",
        ),
        GateRule(
            triggered=up is not None and up < settings.liq_buffer_multiplier_min,
            status=GateStatus.FAIL,
            message=f"Upper liq buffer {up:.2f}x below minimum {settings.liq_buffer_multiplier_min}x" if up else "",
        ),
        GateRule(
            triggered=down is not None and down < settings.liq_buffer_multiplier_min,
            status=GateStatus.FAIL,
            message=f"Lower liq buffer {down:.2f}x below minimum {settings.liq_buffer_multiplier_min}x" if down else "",
        ),
        GateRule(
            triggered=proposal.trend == Trend.NEUTRAL and (up is None or down is None),
            status=GateStatus.FAIL,
            message="Neutral grid missing a liquidation buffer on one side — treat as unverified",
        ),
        GateRule(
            triggered=proposal.trend != Trend.NEUTRAL and not all([up, down]),
            status=GateStatus.FAIL,
            message="Both liquidation buffers are None for a directional grid — cannot confirm safety",
        ),
    ]
