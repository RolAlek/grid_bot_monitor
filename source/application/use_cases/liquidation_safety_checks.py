from source.domain.entities import GateRule, LiquidationEstimate
from source.domain.value_objects import GateStatus, Symbol, Trend
from source.settings import DecisionEngineSettings
from source.utils.ensure import ensure


STOP_LOSS_TOO_CLOSE = "Stop-loss {stop_loss:.2f} too close to price {price:.2f} (<{min_distance_pct:.1f}%)"


def build_liquidation_safety_checks(
    estimate: LiquidationEstimate,
    settings: DecisionEngineSettings,
) -> list[GateRule]:
    proposal = estimate.proposal
    up, down = estimate.buffer_multiplier_up, estimate.buffer_multiplier_down

    rules: list[GateRule] = [
        GateRule(
            triggered=proposal.leverage > settings.leverage_hard_cap,
            status=GateStatus.FAIL,
            message=f"Leverage {proposal.leverage}x exceeds hard cap {settings.leverage_hard_cap}x",
        ),
    ]

    min_distance_pct = 0.005 if proposal.symbol == Symbol.XAUT else 0.01
    min_distance = min_distance_pct * proposal.last_price

    match proposal.trend:
        case Trend.NEUTRAL:
            rules.extend([
                GateRule(
                    triggered=not any([up, down]),
                    status=GateStatus.FAIL,
                    message="Neutral grid missing a liquidation buffer on one side — treat as unverified",
                ),
                GateRule(
                    triggered=up is not None and up < settings.liq_buffer_multiplier_min,
                    status=GateStatus.FAIL,
                    message=f"Upper liq buffer {up:.2f}x below minimum {settings.liq_buffer_multiplier_min}x"
                    if up
                    else "",
                ),
                GateRule(
                    triggered=down is not None and down < settings.liq_buffer_multiplier_min,
                    status=GateStatus.FAIL,
                    message=f"Lower liq buffer {down:.2f}x below minimum {settings.liq_buffer_multiplier_min}x"
                    if down
                    else "",
                ),
            ])
        case Trend.LONG:
            has_sl_tp = proposal.stop_loss is not None and proposal.take_profit is not None
            liq_down = estimate.estimate_liquidation_price_down

            buffer_at_risk = down is not None and down < settings.liq_buffer_multiplier_min
            sl_cant_protect = liq_down is not None and proposal.stop_loss is not None and proposal.stop_loss <= liq_down

            rules.append(
                GateRule(
                    triggered=down is None or (buffer_at_risk and (not has_sl_tp or sl_cant_protect)),
                    status=GateStatus.FAIL,
                    message=(
                        f"Lower liq buffer {down:.2f}x below minimum {settings.liq_buffer_multiplier_min}x"
                        if buffer_at_risk
                        else "Lower liquidation buffer is None — cannot confirm safety"
                    ),
                ),
            )

            if has_sl_tp and liq_down is not None:
                stop_loss = ensure(proposal.stop_loss)
                take_profit = ensure(proposal.take_profit)

                rules.extend([
                    GateRule(
                        triggered=stop_loss <= liq_down,
                        status=GateStatus.FAIL,
                        message=f"Stop-loss {stop_loss:.2f} at/below liquidation {liq_down:.2f}",
                    ),
                    GateRule(
                        triggered=(proposal.last_price - stop_loss) < min_distance,
                        status=GateStatus.CAUTION,
                        message=STOP_LOSS_TOO_CLOSE.format(
                            stop_loss=stop_loss,
                            price=proposal.last_price,
                            min_distance_pct=min_distance_pct,
                        ),
                    ),
                    GateRule(
                        triggered=take_profit < proposal.top,
                        status=GateStatus.CAUTION,
                        message=(
                            f"Take-profit {take_profit:.2f} is below "
                            f"grid top {proposal.top:.2f} — may not capture full move"
                        ),
                    ),
                ])
        case Trend.SHORT:
            has_sl_tp = proposal.stop_loss is not None and proposal.take_profit is not None
            liq_up = estimate.estimate_liquidation_price_up

            buffer_at_risk = up is not None and up < settings.liq_buffer_multiplier_min
            sl_cant_protect = liq_up is not None and proposal.stop_loss is not None and proposal.stop_loss >= liq_up

            rules.append(
                GateRule(
                    triggered=up is None or (buffer_at_risk and (not has_sl_tp or sl_cant_protect)),
                    status=GateStatus.FAIL,
                    message=(
                        f"Upper liq buffer {up:.2f}x below minimum {settings.liq_buffer_multiplier_min}x"
                        if buffer_at_risk
                        else "Upper liquidation buffer is None — cannot confirm safety"
                    ),
                ),
            )

            if has_sl_tp and liq_up is not None:
                stop_loss = ensure(proposal.stop_loss)
                take_profit = ensure(proposal.take_profit)

                rules.extend([
                    GateRule(
                        triggered=stop_loss >= liq_up,
                        status=GateStatus.FAIL,
                        message=f"Stop-loss {stop_loss:.2f} at/above liquidation {liq_up:.2f}",
                    ),
                    GateRule(
                        triggered=(stop_loss - proposal.last_price) < min_distance,
                        status=GateStatus.CAUTION,
                        message=STOP_LOSS_TOO_CLOSE.format(
                            stop_loss=stop_loss,
                            price=proposal.last_price,
                            min_distance_pct=min_distance_pct,
                        ),
                    ),
                    GateRule(
                        triggered=take_profit > proposal.bottom,
                        status=GateStatus.CAUTION,
                        message=(
                            f"Take-profit {take_profit:.2f} is above "
                            f"grid bottom {proposal.bottom:.2f} — may not capture full move"
                        ),
                    ),
                ])

    return rules
