"""System and detection metrics aggregation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Alert, MitigationRecord, MitigationStatus, Prediction, SystemMetric
from ..schemas.metrics import MetricsSummary, PredictionHistoryItem
from ..websockets.manager import ws_manager
from .mitigation_service import mitigation_service

logger = logging.getLogger(__name__)


class MetricsService:
    async def record_metric(self, session: AsyncSession, name: str, value: float) -> None:
        session.add(SystemMetric(metric_name=name, metric_value=value))
        await session.flush()
        await ws_manager.broadcast("metrics", {"type": "metric", "name": name, "value": value, "ts": datetime.now(timezone.utc).isoformat()})

    async def summary(self, session: AsyncSession) -> MetricsSummary:
        preds = await session.execute(select(Prediction))
        all_p = list(preds.scalars().all())
        alerts = await session.execute(select(Alert))
        all_a = list(alerts.scalars().all())

        total = len(all_p)
        attacks = sum(1 for p in all_p if p.is_attack)
        unack = sum(1 for a in all_a if not a.acknowledged)
        avg_lat = sum(p.latency_ms for p in all_p) / total if total else 0.0

        mit_result = await session.execute(
            select(MitigationRecord).where(MitigationRecord.status == MitigationStatus.active)
        )
        active_mit = len(list(mit_result.scalars().all()))
        ps = mitigation_service.prevention_stats
        mit_all = await session.execute(select(MitigationRecord))
        mit_rows = list(mit_all.scalars().all())
        avg_mttm = sum(m.detection_to_action_ms for m in mit_rows) / len(mit_rows) if mit_rows else 0.0

        return MetricsSummary(
            total_predictions=total,
            attack_predictions=attacks,
            benign_predictions=total - attacks,
            total_alerts=len(all_a),
            unacknowledged_alerts=unack,
            avg_latency_ms=round(avg_lat, 3),
            attack_rate=round(attacks / total, 4) if total else 0.0,
            active_mitigations=active_mit,
            flows_blocked=ps["flows_blocked"],
            avg_time_to_mitigate_ms=round(avg_mttm, 2),
        )

    async def prediction_history(self, session: AsyncSession, limit: int = 50) -> list[PredictionHistoryItem]:
        result = await session.execute(select(Prediction).order_by(Prediction.created_at.desc()).limit(limit))
        rows = result.scalars().all()
        return [PredictionHistoryItem.model_validate(r) for r in rows]
