from enum import StrEnum
from types import MappingProxyType
from typing import ClassVar

import structlog

from source.application.exceptions import ClassifierMisconfigurationError
from source.domain.entities.monitoring import ClassificationResult, HealthMetricsInput
from source.domain.value_objects import AlertType, HealthStatus, Symbol
from source.settings import MonitoringSettings


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class Direction(StrEnum):
    HIGHER = "higher_better"
    LOWER = "lower_better"


class HealthClassifier:
    THRESHOLD_OVERRIDES: ClassVar[MappingProxyType[Symbol, dict[str, float]]] = MappingProxyType({
        Symbol.XAUT: {
            "atr_pct_green_max": 2.5,
            "atr_pct_yellow_max": 5.0,
            "liq_distance_green_min_pct": 10.0,
            "liq_distance_yellow_min_pct": 5.0,
            "pnl_green_min_pct": -3.0,
            "pnl_yellow_min_pct": -8.0,
            "fill_green_max": 0.60,
            "fill_yellow_max": 0.85,
        },
        Symbol.XRP: {
            "atr_pct_green_max": 6.0,
            "atr_pct_yellow_max": 12.0,
        },
        Symbol.SOL: {
            "atr_pct_green_max": 7.0,
            "atr_pct_yellow_max": 14.0,
            "liq_distance_green_min_pct": 20.0,
            "liq_distance_yellow_min_pct": 10.0,
        },
    })

    def __init__(self, settings: MonitoringSettings) -> None:
        self._settings = settings

    def classify(self, metrics: HealthMetricsInput) -> ClassificationResult:  # noqa: PLR0914
        overrides = self.THRESHOLD_OVERRIDES.get(metrics.symbol, {})

        liq_status, liq_score = self._eval_threshold(
            metrics.distance_to_liquidation_pct,
            direction=Direction.HIGHER,
            green_min=overrides.get("liq_distance_green_min_pct", self._settings.thresholds.liq_distance_green_min_pct),
            yellow_min=overrides.get(
                "liq_distance_yellow_min_pct",
                self._settings.thresholds.liq_distance_yellow_min_pct,
            ),
        )
        pnl_status, pnl_score = self._eval_threshold(
            metrics.unrealized_pnl_pct,
            direction=Direction.HIGHER,
            green_min=overrides.get("pnl_green_min_pct", self._settings.thresholds.pnl_green_min_pct),
            yellow_min=overrides.get("pnl_yellow_min_pct", self._settings.thresholds.pnl_yellow_min_pct),
        )
        fill_status, fill_score = self._eval_threshold(
            metrics.grid_fill_ratio,
            direction=Direction.LOWER,
            green_max=overrides.get("fill_green_max", self._settings.thresholds.fill_green_max),
            yellow_max=overrides.get("fill_yellow_max", self._settings.thresholds.fill_yellow_max),
        )
        vol_status, vol_score = self._eval_threshold(
            metrics.atr_pct_of_price,
            direction=Direction.LOWER,
            green_max=overrides.get("atr_pct_green_max", self._settings.thresholds.atr_pct_green_max),
            yellow_max=overrides.get("atr_pct_yellow_max", self._settings.thresholds.atr_pct_yellow_max),
        )
        funding_status, funding_score = self._eval_threshold(
            abs(metrics.funding_rate_annualized_pct),
            direction=Direction.LOWER,
            green_max=self._settings.thresholds.funding_green_max_abs_pct,
            yellow_max=self._settings.thresholds.funding_yellow_max_abs_pct,
        )
        adx_status, adx_score = self._eval_threshold(
            metrics.adx14,
            direction=Direction.LOWER,
            green_max=self._settings.thresholds.adx_green_max,
            yellow_max=self._settings.thresholds.adx_yellow_max,
        )

        weights = {
            "liq": self._settings.weights.distance_to_liq,
            "pnl": self._settings.weights.pnl,
            "fill": self._settings.weights.fill_ratio,
            "vol": self._settings.weights.volatility,
            "funding": self._settings.weights.funding,
            "adx": self._settings.weights.adx,
        }
        scores = {
            "liq": liq_score,
            "pnl": pnl_score,
            "fill": fill_score,
            "vol": vol_score,
            "funding": funding_score,
            "adx": adx_score,
        }

        details = {
            "liq_distance": {"value": metrics.distance_to_liquidation_pct, "sub_status": liq_status.name},
            "pnl_pct": {"value": metrics.unrealized_pnl_pct, "sub_status": pnl_status.name},
            "fill_ratio": {"value": metrics.grid_fill_ratio, "sub_status": fill_status.name},
            "atr_pct": {"value": metrics.atr_pct_of_price, "sub_status": vol_status.name},
            "funding_annualized": {"value": metrics.funding_rate_annualized_pct, "sub_status": funding_status.name},
            "adx14": {"value": metrics.adx14, "sub_status": adx_status.name},
        }

        return ClassificationResult(
            status=max((liq_status, pnl_status, fill_status, vol_status, funding_status, adx_status)),
            score=round(sum(scores[k] * weights[k] for k in weights) / sum(weights.values()), 4),
            alerts=tuple(self._determine_alerts(liq_status, pnl_status, fill_status, vol_status, funding_status)),
            details=details,
        )

    def _eval_threshold(  # noqa: PLR0911
        self,
        value: float | None,
        direction: Direction,
        green_min: float | None = None,
        yellow_min: float | None = None,
        green_max: float | None = None,
        yellow_max: float | None = None,
    ) -> tuple[HealthStatus, float]:
        if value is None:
            logger.info("Classifier: metric value is None — treating as neutral (GREEN, 0.5)")
            return HealthStatus.GREEN, 0.5

        if direction == Direction.HIGHER:
            if green_min is None or yellow_min is None:
                logger.critical(
                    "Classifier misconfiguration — higher_better requires green_min and yellow_min",
                    green_min=green_min,
                    yellow_min=yellow_min,
                )
                raise ClassifierMisconfigurationError("green_min and yellow_min required for higher_better")

            if value >= green_min:
                return HealthStatus.GREEN, 1.0

            if value >= yellow_min:
                score = (value - yellow_min) / (green_min - yellow_min)
                logger.warning(
                    "Metric entered YELLOW zone (higher_better)",
                    value=round(value, 4),
                    yellow_min=yellow_min,
                    green_min=green_min,
                    score=round(score, 4),
                )
                return HealthStatus.YELLOW, max(0.0, min(1.0, score))

            # RED zone
            score = max(0.0, value / yellow_min) * 0.3 if yellow_min else 0.0
            logger.warning(
                "Metric in RED zone (higher_better)",
                value=round(value, 4),
                yellow_min=yellow_min,
                red_depth_pct=round(100 * (1 - value / yellow_min) if yellow_min else 100, 1),
                score=round(score, 4),
            )
            return HealthStatus.RED, score

        if green_max is None or yellow_max is None:
            logger.critical(
                "Classifier misconfiguration — lower_better requires green_max and yellow_max",
                green_max=green_max,
                yellow_max=yellow_max,
            )
            raise ClassifierMisconfigurationError("green_max and yellow_max required for lower_better")

        if value <= green_max:
            return HealthStatus.GREEN, 1.0

        if value <= yellow_max:
            score = 1.0 - (value - green_max) / (yellow_max - green_max)
            logger.warning(
                "Metric entered YELLOW zone (lower_better)",
                value=round(value, 4),
                green_max=green_max,
                yellow_max=yellow_max,
                score=round(score, 4),
            )
            return HealthStatus.YELLOW, max(0.0, min(1.0, score))

        # RED zone: score scales 0.3 → 0.0 proportional to how far past yellow_max
        if yellow_max > 0:
            excess = value - yellow_max
            score = max(0.0, 0.3 * (1.0 - excess / yellow_max))
            logger.warning(
                "Metric in RED zone (lower_better)",
                value=round(value, 4),
                yellow_max=yellow_max,
                red_depth_pct=round(100 * excess / yellow_max, 1),
                score=round(score, 4),
            )
        else:
            raise ClassifierMisconfigurationError("yellow_max must be > 0 for lower_better metrics")

        return HealthStatus.RED, score

    @staticmethod
    def _determine_alerts(
        liq_status: HealthStatus,
        pnl_status: HealthStatus,
        fill_status: HealthStatus,
        vol_status: HealthStatus,
        funding_status: HealthStatus,
    ) -> list[AlertType]:
        alerts: list[AlertType] = []
        if liq_status == HealthStatus.RED:
            alerts.append(AlertType.LIQUIDATION_RISK)

        if pnl_status == HealthStatus.RED:
            alerts.append(AlertType.PNL_DRAWDOWN)

        if fill_status == HealthStatus.RED:
            alerts.append(AlertType.GRID_DEPLETION)

        if vol_status == HealthStatus.RED:
            alerts.append(AlertType.VOLATILITY_SPIKE)

        if funding_status == HealthStatus.RED:
            alerts.append(AlertType.HIGH_FUNDING)

        return alerts
