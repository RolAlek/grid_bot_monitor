from datetime import UTC, datetime

from source.application.ports import GridValidationPort, MarketDataPort, NotifierPort
from source.application.services.decision_log_service import DecisionLogService
from source.application.services.indicator_service import IndicatorService
from source.application.services.oi_snapshot_service import OISnapshotService
from source.application.use_cases.assess_liquidation_safety import (
    AssessLiquidationSafety,
)
from source.application.use_cases.assess_market_regime import AssessMarketRegime
from source.application.use_cases.assess_positioning import AssessPositioning
from source.application.use_cases.evaluate_launch_decision import EvaluateLaunchDecision
from source.constants import FUNDING_ANNUALIZATION_FACTOR
from source.domain.value_objects import (
    DecisionVerdict,
    FundingOiSnapshot,
    GateResult,
    ProposedGridParams,
    Symbol,
)
from source.settings import Settings


class RunWeeklyFullAssessment:
    def __init__(
        self,
        market_data: MarketDataPort,
        grid_validation: GridValidationPort,
        indicator_service: IndicatorService,
        decision_service: DecisionLogService,
        oi_service: OISnapshotService,
        gate1: AssessMarketRegime,
        gate2: AssessPositioning,
        gate3: AssessLiquidationSafety,
        evaluator: EvaluateLaunchDecision,
        notifier: NotifierPort,
        settings: Settings,
    ) -> None:
        self._market_data = market_data
        self._decision_service = decision_service
        self._oi_service = oi_service
        self._grid_validation = grid_validation
        self._indicator_service = indicator_service
        self._gate1 = gate1
        self._gate2 = gate2
        self._gate3 = gate3
        self._evaluator = evaluator
        self._notifier = notifier
        self._settings = settings

    async def run(self) -> DecisionVerdict:
        now = datetime.now(UTC)
        symbol = self._settings.pionex.symbol
        interval = self._settings.pionex.kline_interval

        proposal, gate1_verdict = await self._check_first_gate(
            symbol,
            interval,
            self._settings.pionex.limit,
        )
        gate2_verdict = await self._check_second_gate(symbol, now)

        liq_estimate = await self._grid_validation.check_params(proposal)
        gate3_result = self._gate3.assess(liq_estimate)

        verdict = self._evaluator.evaluate(
            symbol=symbol,
            gates=[gate1_verdict, gate2_verdict, gate3_result],
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
        klines = await self._market_data.get_klines(symbol, interval, limit=limit)
        indicators = self._indicator_service.compute(klines, interval)

        proposal = ProposedGridParams(
            top=indicators.swing_high_14d,
            bottom=indicators.swing_low_14d,
            grid_levels=self._settings.decision_engine.default_grid_rows,
            leverage=self._settings.decision_engine.default_leverage,
            quote_investment=self._settings.decision_engine.default_quote_investment,
        )
        result = self._gate1.assess(indicators, proposal)

        return proposal, result

    async def _check_second_gate(self, symbol: Symbol, now: datetime) -> GateResult:
        funding_rows = await self._market_data.get_funding_rates(symbol, limit=1)
        rate = float(funding_rows[-1].rate)
        annualized = rate * FUNDING_ANNUALIZATION_FACTOR
        oi = await self._market_data.get_open_interest(symbol)
        oi_change = await self._oi_service.compute_oi_pct_change_7d(symbol, now)

        snapshot = FundingOiSnapshot(
            symbol=symbol,
            as_of=now,
            funding_rate_last=rate,
            funding_rate_annualized_pct=annualized,
            open_interest=oi.open_interest,
            oi_pct_change_7d=oi_change,
        )
        return self._gate2.assess(snapshot)
