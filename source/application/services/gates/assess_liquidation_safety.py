import logging

from source.application.ports import GridValidationPort
from source.application.use_cases.liquidation_safety_checks import build_liquidation_safety_checks
from source.application.utils import evaluate_checks
from source.domain.entities import GateResult, ProposedGridParams
from source.domain.value_objects import Gate
from source.settings import DecisionEngineSettings


logger = logging.getLogger(__name__)


class AssessLiquidationSafetyService:
    def __init__(
        self,
        settings: DecisionEngineSettings,
        grid_validation: GridValidationPort,
    ) -> None:
        self._settings = settings
        self._grid_validation = grid_validation

    async def execute(self, proposal: ProposedGridParams) -> GateResult:
        liquidation_estimate = await self._grid_validation.check_grid_params(proposal)
        checks = build_liquidation_safety_checks(liquidation_estimate, self._settings)
        status, reasons = evaluate_checks(checks)

        return GateResult(
            gate=Gate.LIQUIDATION_SAFETY,
            status=status,
            reasons=reasons,
            raw_values={
                "leverage": liquidation_estimate.proposal.leverage,
                "estimate_liquidation_price_up": liquidation_estimate.estimate_liquidation_price_up,
                "estimate_liquidation_price_down": liquidation_estimate.estimate_liquidation_price_down,
                "buffer_multiplier_up": liquidation_estimate.buffer_multiplier_up,
                "buffer_multiplier_down": liquidation_estimate.buffer_multiplier_down,
            },
        )
