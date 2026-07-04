"""Alert and prediction repositories."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Alert, AlertSeverity, Prediction


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        victim_ip: str,
        model_name: str,
        is_attack: bool,
        probability: float,
        num_nodes: int,
        num_edges: int,
        num_flows: int,
        latency_ms: float,
    ) -> Prediction:
        row = Prediction(
            victim_ip=victim_ip,
            model_name=model_name,
            is_attack=is_attack,
            probability=probability,
            num_nodes=num_nodes,
            num_edges=num_edges,
            num_flows=num_flows,
            latency_ms=latency_ms,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_recent(self, limit: int = 50) -> list[Prediction]:
        result = await self.session.execute(select(Prediction).order_by(desc(Prediction.created_at)).limit(limit))
        return list(result.scalars().all())


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        victim_ip: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        probability: float,
        prediction_id: int | None = None,
    ) -> Alert:
        alert = Alert(
            victim_ip=victim_ip,
            severity=severity,
            title=title,
            message=message,
            probability=probability,
            prediction_id=prediction_id,
        )
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def list_recent(self, limit: int = 50, unacknowledged_only: bool = False) -> list[Alert]:
        q = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
        if unacknowledged_only:
            q = q.where(Alert.acknowledged.is_(False))
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def acknowledge(self, alert_id: int) -> Alert | None:
        result = await self.session.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if alert:
            alert.acknowledged = True
            await self.session.flush()
        return alert
