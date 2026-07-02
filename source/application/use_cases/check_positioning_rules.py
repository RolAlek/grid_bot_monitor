from source.domain.entities import FundingOiSnapshot, GateRule
from source.domain.value_objects import GateStatus, Trend
from source.settings import DecisionEngineSettings


def build_positioning_checks(
    snapshot: FundingOiSnapshot,
    settings: DecisionEngineSettings,
) -> list[GateRule]:
    funding = snapshot.funding_rate_annualized_pct
    oi_change = snapshot.oi_pct_change_7d

    checks = [
        GateRule(
            triggered=abs(funding) > settings.funding_annualized_fail_pct,
            status=GateStatus.FAIL,
            message=(
                f"Funding {funding:.1f}% annualized exceeds ±{settings.funding_annualized_fail_pct}% fail threshold"
            ),
        ),
        GateRule(
            triggered=settings.funding_annualized_caution_pct < abs(funding) <= settings.funding_annualized_fail_pct,
            status=GateStatus.CAUTION,
            message=f"Funding {funding:.1f}% annualized in caution zone (±{settings.funding_annualized_caution_pct}%)",
        ),
        GateRule(
            triggered=oi_change is None,
            status=GateStatus.CAUTION,
            message="Insufficient OI history — less than 7 days of stored data",
        ),
    ]

    if oi_change is not None:
        crowded_long = funding > settings.funding_annualized_caution_pct and oi_change > 0
        crowded_short = funding < -settings.funding_annualized_caution_pct and oi_change > 0
        direction = Trend.LONG if crowded_long else Trend.SHORT

        checks.extend((
            GateRule(
                triggered=(crowded_long or crowded_short) and oi_change > settings.oi_7d_change_fail_pct,
                status=GateStatus.FAIL,
                message=f"Crowded {direction}: OI +{oi_change:.1f}% in 7d with extreme funding {funding:.1f}%",
            ),
            GateRule(
                triggered=not (crowded_long or crowded_short) and oi_change > settings.oi_7d_change_caution_pct,
                status=GateStatus.CAUTION,
                message=f"OI +{oi_change:.1f}% in 7d — building faster than usual, watch for crowding",
            ),
        ))

    return checks
