import pytest

from source.application.services.health_classifier import HealthClassifier
from source.domain.entities.monitoring import HealthMetricsInput
from source.domain.value_objects import AlertType, HealthStatus, Symbol
from source.settings import MonitoringSettings


@pytest.fixture
def classifier() -> HealthClassifier:
    return HealthClassifier(MonitoringSettings())


def _make_input(**overrides: float | str) -> HealthMetricsInput:
    defaults: dict[str, float | str | int] = {
        "symbol": Symbol.BTC,
        "last_price": 95_000.0,
        "leverage": 2,
        "adx14": 18.0,
        "atr14": 1_500.0,
        "atr_pct_of_price": 1.5,
        "rsi14": 52.0,
        "realized_vol_1d": 0.02,
        "realized_vol_7d": 0.018,
        "unrealized_pnl": 250.0,
        "unrealized_pnl_pct": 2.5,
        "grid_fill_ratio": 0.40,
        "distance_to_liquidation_pct": 25.0,
        "funding_rate_annualized_pct": 5.0,
    }
    defaults.update(overrides)
    return HealthMetricsInput(**defaults)  # type: ignore[arg-type]


class TestHealthClassifier:
    def test_all_green_metrics(self, classifier: HealthClassifier) -> None:
        result = classifier.classify(_make_input())
        assert result.status == HealthStatus.GREEN
        assert result.score > 0.9

    def test_one_red_dominates(self, classifier: HealthClassifier) -> None:
        result = classifier.classify(_make_input(distance_to_liquidation_pct=3.0))
        assert result.status == HealthStatus.RED

    def test_xaut_atr_override(self, classifier: HealthClassifier) -> None:
        """XAUT ATR 3% → YELLOW (without override would be GREEN at default 5% threshold)."""
        result = classifier.classify(_make_input(symbol=Symbol.XAUT, atr_pct_of_price=3.0))
        assert result.status == HealthStatus.YELLOW

    def test_sol_liq_override(self, classifier: HealthClassifier) -> None:
        """SOL liq_distance 12% → YELLOW (without override would be GREEN at default 15%)."""
        result = classifier.classify(_make_input(symbol=Symbol.SOL, distance_to_liquidation_pct=12.0))
        assert result.status == HealthStatus.YELLOW

    def test_weighted_score(self, classifier: HealthClassifier) -> None:
        result = classifier.classify(_make_input())
        assert 0.0 <= result.score <= 1.0

    def test_alerts_for_red_metrics(self, classifier: HealthClassifier) -> None:
        result = classifier.classify(_make_input(grid_fill_ratio=0.95, distance_to_liquidation_pct=3.0))
        assert AlertType.GRID_DEPLETION in result.alerts
        assert AlertType.LIQUIDATION_RISK in result.alerts

    def test_funding_yellow(self, classifier: HealthClassifier) -> None:
        result = classifier.classify(_make_input(funding_rate_annualized_pct=-25.0))
        assert result.status == HealthStatus.YELLOW

    def test_funding_red(self, classifier: HealthClassifier) -> None:
        result = classifier.classify(_make_input(funding_rate_annualized_pct=35.0))
        assert result.status == HealthStatus.RED
        assert AlertType.HIGH_FUNDING in result.alerts

    def test_fill_ratio_yellow(self, classifier: HealthClassifier) -> None:
        result = classifier.classify(_make_input(grid_fill_ratio=0.80))
        assert result.status == HealthStatus.YELLOW

    def test_details_contain_all_metrics(self, classifier: HealthClassifier) -> None:
        result = classifier.classify(_make_input())
        assert "liq_distance" in result.details
        assert "pnl_pct" in result.details
        assert "fill_ratio" in result.details
        assert "atr_pct" in result.details
        assert "funding_annualized" in result.details
        assert "adx14" in result.details
