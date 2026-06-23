from source.domain.entities import GateResult, LiquidationEstimate
from source.domain.value_objects import Gate, GateStatus, Trend
from source.settings import DecisionEngineSettings


class AssessLiquidationSafety:
    def __init__(self, settings: DecisionEngineSettings) -> None:
        self._settings: DecisionEngineSettings = settings

    def assess(self, estimate: LiquidationEstimate) -> GateResult:
        reasons: list[str] = []
        fail = False

        if (
            estimate.buffer_multiplier_up is not None
            and estimate.buffer_multiplier_up < self._settings.liq_buffer_multiplier_min
        ):
            fail = True
            reasons.append(
                f"Upper liq buffer {estimate.buffer_multiplier_up:.2f}x "
                f"below minimum {self._settings.liq_buffer_multiplier_min}x"
            )

        # Lower liquidation buffer
        if (
            estimate.buffer_multiplier_down is not None
            and estimate.buffer_multiplier_down < self._settings.liq_buffer_multiplier_min
        ):
            fail = True
            reasons.append(
                f"Lower liq buffer {estimate.buffer_multiplier_down:.2f}x "
                f"below minimum {self._settings.liq_buffer_multiplier_min}x"
            )

        if estimate.proposal.trend == Trend.NEUTRAL and (
            estimate.buffer_multiplier_up is None or estimate.buffer_multiplier_down is None
        ):
            fail = True
            reasons.append("Neutral grid missing a liquidation buffer on one side — treat as unverified")

        return GateResult(
            gate=Gate.LIQUIDATION_SAFETY,
            status=GateStatus.FAIL if fail else GateStatus.PASS,
            reasons=tuple(reasons),
            raw_values={
                "leverage": estimate.proposal.leverage,
                "estimate_liquidation_price_up": estimate.estimate_liquidation_price_up,
                "estimate_liquidation_price_down": estimate.estimate_liquidation_price_down,
                "buffer_multiplier_up": estimate.buffer_multiplier_up,
                "buffer_multiplier_down": estimate.buffer_multiplier_down,
            },
        )
