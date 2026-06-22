from source.domain.entities import (
    Gate,
    GateResult,
    GateStatus,
    LiquidationEstimate,
)
from source.settings import DecisionEngineSettings


class AssessLiquidationSafety:
    """Gate 3 — Liquidation safety (§6).

    LiquidationEstimate must be freshly obtained from checkParams immediately
    before this gate runs — its values are price-dependent and go stale fast.
    """

    def __init__(self, settings: DecisionEngineSettings) -> None:
        self._s = settings

    def assess(self, estimate: LiquidationEstimate) -> GateResult:
        reasons: list[str] = []
        fail = False

        # Upper liquidation buffer
        if (
            estimate.buffer_multiplier_up is not None
            and estimate.buffer_multiplier_up < self._s.liq_buffer_multiplier_min
        ):
            fail = True
            reasons.append(
                f"Upper liq buffer {estimate.buffer_multiplier_up:.2f}x "
                f"below minimum {self._s.liq_buffer_multiplier_min}x"
            )

        # Lower liquidation buffer
        if (
            estimate.buffer_multiplier_down is not None
            and estimate.buffer_multiplier_down < self._s.liq_buffer_multiplier_min
        ):
            fail = True
            reasons.append(
                f"Lower liq buffer {estimate.buffer_multiplier_down:.2f}x "
                f"below minimum {self._s.liq_buffer_multiplier_min}x"
            )

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
