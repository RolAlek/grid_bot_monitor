from datetime import UTC, datetime

from source.application.ports import GridValidationPort, MarketDataPort, NotifierPort
from source.application.services.decision_log_service import DecisionLogService
from source.application.services.grid_builder import GridProposalBuilder
from source.application.services.indicator_service import IndicatorService
from source.application.services.oi_snapshot_service import OISnapshotService
from source.application.use_cases.assess_liquidation_safety import AssessLiquidationSafety
from source.application.use_cases.assess_market_regime import AssessMarketRegime
from source.application.use_cases.assess_positioning import AssessPositioning
from source.application.use_cases.checkers.base import BaseChecker
from source.domain.entities import DecisionVerdict, GateResult, ProposedGridParams
from source.domain.value_objects import GateStatus, Symbol, VerdictAction
from source.settings import Settings


class RunWeeklyFullAssessment(BaseChecker):
    def __init__(
        self,
        market_data: MarketDataPort,
        grid_validation: GridValidationPort,
        indicator_service: IndicatorService,
        decision_service: DecisionLogService,
        oi_service: OISnapshotService,
        grid_builder: GridProposalBuilder,
        gate1: AssessMarketRegime,
        gate2: AssessPositioning,
        gate3: AssessLiquidationSafety,
        notifier: NotifierPort,
        settings: Settings,
    ) -> None:
        super().__init__(market_data, gate2, oi_service)

        self._decision_service = decision_service
        self._grid_validation = grid_validation
        self._indicator_service = indicator_service
        self._grid_builder = grid_builder
        self._gate1 = gate1
        self._gate3 = gate3
        self._notifier = notifier
        self._settings = settings

    async def run(self) -> DecisionVerdict:
        now = datetime.now(UTC)
        symbol = self._settings.pionex.symbol
        interval = self._settings.pionex.kline_interval

        proposal, gate1_verdict = await self._check_first_gate(
            symbol=symbol,
            interval=interval,
            limit=self._settings.pionex.limit,
        )
        gate2_result, _ = await self.check_second_gate(symbol, now, is_save=False)

        liq_estimate = await self._grid_validation.check_grid_params(proposal)
        gate3_result = self._gate3.assess(liq_estimate)

        verdict = self._resolve(
            symbol=symbol,
            gates=[gate1_verdict, gate2_result, gate3_result],
            proposal=proposal,
            notes="weekly full assessment",
        )

        await self._decision_service.persist_verdict(verdict)
        await self._notifier.send_digest(verdict)

        return verdict

    async def _check_first_gate(
        self,
        symbol: Symbol,
        interval: str,
        limit: int,
    ) -> tuple[ProposedGridParams, GateResult]:
        candles = await self._market_data.get_candles(symbol, interval, limit=limit)
        indicators = self._indicator_service.compute(candles, interval)
        proposal = self._grid_builder.build(symbol, indicators)
        result = self._gate1.assess(indicators, proposal)

        return proposal, result

    def _resolve(
        self,
        symbol: Symbol,
        gates: list[GateResult],
        notes: str | None,
        proposal: ProposedGridParams | None = None,
    ) -> DecisionVerdict:
        if any(gate.status == GateStatus.FAIL for gate in gates):
            action = VerdictAction.HOLD
        elif any(gate.status == GateStatus.CAUTION for gate in gates):
            action = VerdictAction.REVIEW
        else:
            action = VerdictAction.LAUNCH

        return DecisionVerdict(
            as_of=datetime.now(UTC),
            symbol=symbol,
            action=action,
            gates=tuple(gates),
            suggested_grid_top=proposal.top if proposal else None,
            suggested_grid_bottom=proposal.bottom if proposal else None,
            suggested_leverage=proposal.leverage if proposal else None,
            notes=notes,
        )
