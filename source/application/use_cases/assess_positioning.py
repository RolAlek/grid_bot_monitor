from source.domain.value_objects import FundingOiSnapshot, Gate, GateResult, GateStatus
from source.settings import DecisionEngineSettings


class AssessPositioning:
    """Gate 2 — Positioning."""

    def __init__(self, settings: DecisionEngineSettings) -> None:
        self._settings = settings

    def assess(self, snapshot: FundingOiSnapshot) -> GateResult:
        reasons: list[str] = []
        statuses: list[GateStatus] = [GateStatus.PASS]

        funding = snapshot.funding_rate_annualized_pct
        oi_change = snapshot.oi_pct_change_7d

        # Funding rate extremes
        if abs(funding) > self._settings.funding_annualized_fail_pct:
            statuses.append(GateStatus.FAIL)
            reasons.append(
                f"Funding {funding:.1f}% annualized exceeds"
                f" ±{self._settings.funding_annualized_fail_pct}% fail threshold"
            )
        elif abs(funding) > self._settings.funding_annualized_caution_pct:
            statuses.append(GateStatus.CAUTION)
            reasons.append(
                f"Funding {funding:.1f}% annualized in caution zone (±{self._settings.funding_annualized_caution_pct}%)"
            )

        # Insufficient OI history — conservative, not a free pass
        if oi_change is None:
            statuses.append(GateStatus.CAUTION)
            reasons.append("Insufficient OI history — less than 7 days of stored data")
        else:
            crowded_long = funding > self._settings.funding_annualized_caution_pct and oi_change > 0
            crowded_short = funding < -self._settings.funding_annualized_caution_pct and oi_change > 0

            if (crowded_long or crowded_short) and oi_change > self._settings.oi_7d_change_fail_pct:
                statuses.append(GateStatus.FAIL)
                direction = "long" if crowded_long else "short"
                reasons.append(f"Crowded {direction}: OI +{oi_change:.1f}% in 7d with extreme funding {funding:.1f}%")

        return GateResult(
            gate=Gate.POSITIONING,
            status=max(statuses),
            reasons=tuple(reasons),
            raw_values={
                "funding_rate_annualized_pct": funding,
                "oi_pct_change_7d": oi_change,
                "open_interest": snapshot.open_interest,
            },
        )
