from datetime import UTC, datetime
from uuid import uuid4

from source.application.ports import MarketDataPort, NotifierPort
from source.application.services.decision_history_service import DecisionHistoryService
from source.application.use_cases.assess_positioning import AssessPositioning
from source.domain.value_objects import (
    DecisionVerdict,
    FundingOiSnapshot,
    GateResult,
    GateStatus,
    Symbol,
    VerdictAction,
)
from source.settings import DecisionEngineSettings

ALERT_EMOJI = {"PASS": "🟢", "CAUTION": "🟡", "FAIL": "🔴"}
ALERT_TEMPLATE = (
    "{emoji} Gate status change — Positioning (Gate 2)\n"
    "Funding: {funding_rate:.1f}% annualized ({direction})\n"
    "OI 7d change: {oi_change}\n"
    "Previous: {prev_status} → Now: {current_status}\n"
    "No action taken — informational only."
)


class RunDailyPositioningCheck:
    _FUNDING_ANNUALIZATION_FACTOR = 3 * 365 * 100

    def __init__(
        self,
        market_data: MarketDataPort,
        history: DecisionHistoryService,
        gate2: AssessPositioning,
        notifier: NotifierPort,
        settings: DecisionEngineSettings,
    ) -> None:
        self._market_data = market_data
        self._history = history
        self._gate2 = gate2
        self._notifier = notifier
        self._settings = settings

    async def run(self) -> GateResult:
        now = datetime.now(UTC)
        symbol = self._settings.symbol

        # Fetch and persist OI snapshot (feeds the 7-day rolling history)
        oi = await self._market_data.get_open_interest(symbol)
        await self._history.persist_oi_snapshot(symbol, now, float(oi.open_interest))

        # Latest funding rate
        funding_rows = await self._market_data.get_funding_rates(symbol, limit=1)
        rate = float(funding_rows[-1].rate)
        annualized = rate * self._FUNDING_ANNUALIZATION_FACTOR

        oi_change = await self._history.compute_oi_pct_change_7d(symbol, now)

        snapshot = FundingOiSnapshot(
            symbol=symbol,
            as_of=now,
            funding_rate_last=rate,
            funding_rate_annualized_pct=annualized,
            open_interest=float(oi.open_interest),
            oi_pct_change_7d=oi_change,
        )
        gate_result = self._gate2.assess(snapshot)

        # Compare against yesterday's Gate 2 status (None if no prior run)
        prev_status = await self._previous_gate2_status(symbol)
        if gate_result.status != prev_status:
            alert = self._format_alert(snapshot, gate_result, prev_status)
            await self._notifier.send_alert(alert)

        # Persist a positioning-only verdict so tomorrow's run can compare
        await self._history.persist_verdict(
            DecisionVerdict(
                decision_id=uuid4(),
                as_of=now,
                symbol=symbol,
                action=VerdictAction.HOLD
                if gate_result.status == GateStatus.FAIL
                else VerdictAction.REVIEW
                if gate_result.status == GateStatus.CAUTION
                else VerdictAction.LAUNCH,
                gates=[gate_result],
                suggested_grid_top=None,
                suggested_grid_bottom=None,
                suggested_leverage=None,
                notes="daily positioning check",
            )
        )

        return gate_result

    async def _previous_gate2_status(self, symbol: Symbol) -> GateStatus | None:
        last = await self._history._repository.get_last_decision(symbol)
        if last is None:
            return None
        for gate in last.gates:
            if gate.gate == "positioning":
                return gate.status
        return None

    @staticmethod
    def _format_alert(
        snapshot: FundingOiSnapshot,
        result: GateResult,
        prev_status: GateStatus | None,
    ) -> str:
        direction = "long" if snapshot.funding_rate_annualized_pct > 0 else "short"
        oi_str = (
            f"{snapshot.oi_pct_change_7d:.1f}%" if snapshot.oi_pct_change_7d else None
        )
        prev_str = prev_status.name if prev_status else "NONE"
        emoji = ALERT_EMOJI.get(result.status.name, "⚪")

        return ALERT_TEMPLATE.format(
            emoji,
            snapshot.funding_rate_annualized_pct,
            direction,
            oi_str,
            prev_str,
            result.status.name,
        )

    @staticmethod
    def _resolve_action(status: GateStatus) -> VerdictAction:
        match status:
            case GateStatus.FAIL:
                return VerdictAction.HOLD
            case GateStatus.CAUTION:
                return VerdictAction.REVIEW
            case GateStatus.PASS:
                return VerdictAction.LAUNCH
