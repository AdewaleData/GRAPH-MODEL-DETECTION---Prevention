"""Prevention policy engine — auto-mitigate on detection, manual apply/revoke."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from torch_geometric.data import Data

from ..core.config import (
    MITIGATION_AUTO_ENABLED,
    MITIGATION_BLOCK_TOP_K,
    MITIGATION_MODE,
    MITIGATION_QUARANTINE_TOP_K,
    MITIGATION_RATE_LIMIT_TOP_K,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
)
from ..db.models import AlertSeverity, MitigationActionType
from ..db.repositories.mitigation_repository import MitigationRepository
from ..schemas.predict import FlowRecord
from ..websockets.manager import ws_manager
from .blocklist_service import blocklist_service
from .mitigation_actuator import mitigation_actuator
from .source_ranker import rank_attacker_sources

logger = logging.getLogger(__name__)

_flows_blocked_count = 0
_flows_allowed_count = 0


class MitigationService:
    def _action_for_severity(self, severity: AlertSeverity) -> tuple[MitigationActionType, int]:
        if severity == AlertSeverity.critical:
            return MitigationActionType.block, MITIGATION_BLOCK_TOP_K
        if severity == AlertSeverity.high:
            return MitigationActionType.rate_limit, MITIGATION_RATE_LIMIT_TOP_K
        return MitigationActionType.quarantine, MITIGATION_QUARANTINE_TOP_K

    async def maybe_auto_mitigate(
        self,
        session: AsyncSession,
        *,
        victim_ip: str,
        probability: float,
        severity: AlertSeverity,
        flows: list[FlowRecord],
        graph_data: Data | None,
        node_ips: list[str] | None,
        alert_id: int | None,
        prediction_id: int | None,
        detection_started_at: float,
    ) -> list[dict]:
        global _flows_blocked_count, _flows_allowed_count
        if not MITIGATION_AUTO_ENABLED:
            return []

        action_type, top_k = self._action_for_severity(severity)
        ranked = rank_attacker_sources(flows, victim_ip, graph_data, node_ips, top_k=top_k)
        if not ranked:
            logger.warning("No attacker sources ranked for victim=%s", victim_ip)
            return []

        elapsed_ms = (time.perf_counter() - detection_started_at) * 1000
        payloads: list[dict] = []
        repo = MitigationRepository(session)

        for source_ip, score, meta in ranked:
            if blocklist_service.is_blocked(source_ip):
                continue

            reason = (
                f"Auto-{action_type.value}: prob={probability:.1%}, severity={severity.value}, "
                f"flows={meta.get('flows', 0)}, packets/s={meta.get('packets_s', 0):.0f}"
            )
            record = await self._apply(
                session,
                repo,
                source_ip=source_ip,
                victim_ip=victim_ip,
                action=action_type,
                reason=reason,
                score=score,
                alert_id=alert_id,
                prediction_id=prediction_id,
                auto_triggered=True,
                detection_to_action_ms=elapsed_ms,
            )
            payloads.append(record)
            if action_type == MitigationActionType.block:
                _flows_blocked_count += sum(1 for f in flows if f.source_ip == source_ip)
        return payloads

    async def apply_manual(
        self,
        session: AsyncSession,
        source_ip: str,
        victim_ip: str,
        action: MitigationActionType,
        reason: str,
    ) -> dict:
        repo = MitigationRepository(session)
        return await self._apply(
            session,
            repo,
            source_ip=source_ip,
            victim_ip=victim_ip,
            action=action,
            reason=reason,
            score=0.0,
            auto_triggered=False,
            detection_to_action_ms=0.0,
        )

    async def revoke(self, session: AsyncSession, record_id: int | None = None, source_ip: str | None = None) -> list[dict]:
        repo = MitigationRepository(session)
        records = []
        if record_id:
            r = await repo.revoke(record_id)
            if r:
                records = [r]
        elif source_ip:
            records = await repo.revoke_by_source(source_ip)
        else:
            return []

        payloads = []
        for r in records:
            await mitigation_actuator.revoke(r.source_ip, r.action)
            blocklist_service.remove(r.source_ip)
            payload = self._to_payload(r)
            payloads.append(payload)
            await ws_manager.broadcast("mitigation", {"type": "mitigation_revoked", **payload})
        return payloads

    async def load_blocklist(self, session: AsyncSession) -> None:
        repo = MitigationRepository(session)
        active = await repo.list_active(limit=500)
        blocklist_service.sync_from_records(active)

    def filter_flows(self, flows: list[FlowRecord]) -> tuple[list[FlowRecord], list[str]]:
        global _flows_blocked_count, _flows_allowed_count
        allowed: list[FlowRecord] = []
        blocked_sources: list[str] = []

        for flow in flows:
            entry = blocklist_service.is_mitigated(flow.source_ip)
            if entry and entry.get("action") == MitigationActionType.block.value:
                blocked_sources.append(flow.source_ip)
                _flows_blocked_count += 1
            else:
                allowed.append(flow)
                _flows_allowed_count += 1
        return allowed, blocked_sources

    @property
    def prevention_stats(self) -> dict:
        return {
            "flows_blocked": _flows_blocked_count,
            "flows_allowed": _flows_allowed_count,
        }

    async def summary(self, session: AsyncSession) -> dict:
        repo = MitigationRepository(session)
        all_records = await repo.list_recent(limit=1000)
        active = [r for r in all_records if r.status.value == "active"]
        revoked = [r for r in all_records if r.status.value == "revoked"]
        bl = blocklist_service.stats
        return {
            "active_blocks": bl["blocked"],
            "active_rate_limits": bl["rate_limited"],
            "active_quarantines": bl["quarantined"],
            "total_active": bl["total_active"],
            "total_applied": len(all_records),
            "total_revoked": len(revoked),
            "avg_time_to_mitigate_ms": round(await repo.avg_time_to_mitigate(), 2),
            "mode": MITIGATION_MODE,
            "auto_enabled": MITIGATION_AUTO_ENABLED,
        }

    async def _apply(
        self,
        session: AsyncSession,
        repo: MitigationRepository,
        *,
        source_ip: str,
        victim_ip: str,
        action: MitigationActionType,
        reason: str,
        score: float,
        alert_id: int | None = None,
        prediction_id: int | None = None,
        auto_triggered: bool = True,
        detection_to_action_ms: float = 0.0,
    ) -> dict:
        actuator_result = await mitigation_actuator.apply(source_ip, action, victim_ip, reason)
        rule_text = None
        if isinstance(actuator_result, dict):
            sim = actuator_result.get("simulated", actuator_result)
            rule_text = sim.get("rule") if isinstance(sim, dict) else None

        record = await repo.create(
            source_ip=source_ip,
            victim_ip=victim_ip,
            action=action,
            reason=reason,
            score=score,
            rule_text=rule_text,
            alert_id=alert_id,
            prediction_id=prediction_id,
            auto_triggered=auto_triggered,
            detection_to_action_ms=detection_to_action_ms,
        )
        blocklist_service.add(source_ip, action, victim_ip, record.id)
        payload = self._to_payload(record)
        payload["actuator_result"] = actuator_result
        await ws_manager.broadcast("mitigation", {"type": "mitigation_applied", **payload})
        logger.info(
            "Mitigation applied id=%s action=%s source=%s victim=%s auto=%s",
            record.id,
            action.value,
            source_ip,
            victim_ip,
            auto_triggered,
        )
        return payload

    @staticmethod
    def _to_payload(record) -> dict:
        return {
            "id": record.id,
            "source_ip": record.source_ip,
            "victim_ip": record.victim_ip,
            "action": record.action.value,
            "status": record.status.value,
            "score": record.score,
            "reason": record.reason,
            "rule_text": record.rule_text,
            "alert_id": record.alert_id,
            "prediction_id": record.prediction_id,
            "auto_triggered": record.auto_triggered,
            "detection_to_action_ms": record.detection_to_action_ms,
            "applied_at": record.applied_at.isoformat() if record.applied_at else datetime.now(timezone.utc).isoformat(),
            "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
        }


mitigation_service = MitigationService()
