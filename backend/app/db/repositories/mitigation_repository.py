"""Mitigation record repository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import MitigationActionType, MitigationRecord, MitigationStatus


class MitigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        source_ip: str,
        victim_ip: str,
        action: MitigationActionType,
        reason: str,
        score: float = 0.0,
        rule_text: str | None = None,
        alert_id: int | None = None,
        prediction_id: int | None = None,
        auto_triggered: bool = True,
        detection_to_action_ms: float = 0.0,
    ) -> MitigationRecord:
        record = MitigationRecord(
            source_ip=source_ip,
            victim_ip=victim_ip,
            action=action,
            status=MitigationStatus.active,
            score=score,
            reason=reason,
            rule_text=rule_text,
            alert_id=alert_id,
            prediction_id=prediction_id,
            auto_triggered=auto_triggered,
            detection_to_action_ms=detection_to_action_ms,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get(self, record_id: int) -> MitigationRecord | None:
        result = await self.session.execute(select(MitigationRecord).where(MitigationRecord.id == record_id))
        return result.scalar_one_or_none()

    async def list_active(self, limit: int = 100) -> list[MitigationRecord]:
        result = await self.session.execute(
            select(MitigationRecord)
            .where(MitigationRecord.status == MitigationStatus.active)
            .order_by(desc(MitigationRecord.applied_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 100) -> list[MitigationRecord]:
        result = await self.session.execute(
            select(MitigationRecord).order_by(desc(MitigationRecord.applied_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def revoke(self, record_id: int) -> MitigationRecord | None:
        record = await self.get(record_id)
        if record and record.status == MitigationStatus.active:
            record.status = MitigationStatus.revoked
            record.revoked_at = datetime.now(timezone.utc)
            await self.session.flush()
        return record

    async def revoke_by_source(self, source_ip: str) -> list[MitigationRecord]:
        result = await self.session.execute(
            select(MitigationRecord).where(
                MitigationRecord.source_ip == source_ip,
                MitigationRecord.status == MitigationStatus.active,
            )
        )
        rows = list(result.scalars().all())
        now = datetime.now(timezone.utc)
        for r in rows:
            r.status = MitigationStatus.revoked
            r.revoked_at = now
        await self.session.flush()
        return rows

    async def count_active(self) -> int:
        result = await self.session.execute(
            select(MitigationRecord).where(MitigationRecord.status == MitigationStatus.active)
        )
        return len(list(result.scalars().all()))

    async def avg_time_to_mitigate(self) -> float:
        result = await self.session.execute(select(MitigationRecord))
        rows = list(result.scalars().all())
        if not rows:
            return 0.0
        return sum(r.detection_to_action_ms for r in rows) / len(rows)
