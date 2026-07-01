from source.domain.entities import GateRule, LiquidationEstimate
from source.domain.value_objects import GateStatus, Symbol, Trend
from source.settings import DecisionEngineSettings


STOP_LOSS_TOO_CLOSE = "Stop-loss {stop_loss:.2f} too close to price {price:.2f} (<{min_distance_pct:.1f}%)"


def build_liquidation_safety_checks(
    estimate: LiquidationEstimate,
    settings: DecisionEngineSettings,
) -> list[GateRule]:
    proposal = estimate.proposal
    up, down = estimate.buffer_multiplier_up, estimate.buffer_multiplier_down

    rules = [
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

    min_distance_pct = 0.005 if proposal.symbol == Symbol.XAUT else 0.01
    min_distance = min_distance_pct * proposal.last_price

    if proposal.trend == Trend.LONG and proposal.stop_loss and proposal.take_profit:
        rules.extend([
            GateRule(
                triggered=down is not None and proposal.stop_loss <= down,
                status=GateStatus.FAIL,
                message=f"Stop-loss {proposal.stop_loss:.2f} at/below liquidation {down:.2f}",
            ),
            GateRule(
                triggered=(proposal.last_price - proposal.stop_loss) < min_distance,
                status=GateStatus.CAUTION,
                message=STOP_LOSS_TOO_CLOSE.format(
                    stop_lose=proposal.stop_loss, price=proposal.last_price, min_distance_pct=min_distance_pct
                ),
            ),
            GateRule(
                triggered=proposal.take_profit < proposal.top,
                status=GateStatus.CAUTION,
                message=(
                    f"Take-profit {proposal.take_profit:.2f} is below "
                    f"grid top {proposal.top:.2f} — may not capture full move"
                ),
            ),
        ])

    if proposal.trend == Trend.SHORT and proposal.stop_loss and proposal.take_profit:
        rules.extend([
            GateRule(
                triggered=up is not None and proposal.stop_loss >= up,
                status=GateStatus.FAIL,
                message=f"Stop-loss {proposal.stop_loss:.2f} at/above liquidation {up:.2f}",
            ),
            GateRule(
                triggered=(proposal.stop_loss - proposal.last_price) < min_distance,
                status=GateStatus.CAUTION,
                message=STOP_LOSS_TOO_CLOSE.format(
                    stop_lose=proposal.stop_loss, price=proposal.last_price, min_distance_pct=min_distance_pct
                ),
            ),
            GateRule(
                triggered=proposal.take_profit > proposal.bottom,
                status=GateStatus.CAUTION,
                message=(
                    f"Take-profit {proposal.take_profit:.2f} is above "
                    f"grid bottom {proposal.bottom:.2f} — may not capture full move"
                ),
            ),
        ])

    return rules
