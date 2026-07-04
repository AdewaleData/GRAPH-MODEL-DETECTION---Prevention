"""Alert creation and severity classification."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import ALERT_PROB_THRESHOLD, SEVERITY_HIGH, SEVERITY_MEDIUM
from ..db.models import AlertSeverity
from ..db.repositories.alert_repository import AlertRepository
from ..websockets.manager import ws_manager

logger = logging.getLogger(__name__)


class AlertService:
    async def maybe_create_alert(
        self,
        session: AsyncSession,
        victim_ip: str,
        probability: float,
        is_attack: bool,
        prediction_id: int | None = None,
    ) -> dict | None:
        if not is_attack or probability < ALERT_PROB_THRESHOLD:
            return None

        if probability >= SEVERITY_HIGH:
            severity = AlertSeverity.critical
            title = "Critical DDoS pattern detected"
        elif probability >= SEVERITY_MEDIUM:
            severity = AlertSeverity.high
            title = "High-risk traffic window"
        else:
            severity = AlertSeverity.medium
            title = "Suspicious traffic window"

        message = f"Elevated attack probability ({probability:.1%}) on victim {victim_ip}"
        repo = AlertRepository(session)
        alert = await repo.create(victim_ip, severity, title, message, probability, prediction_id)
        logger.info("Alert created id=%s victim=%s severity=%s", alert.id, victim_ip, severity.value)

        payload = {
            "type": "alert",
            "id": alert.id,
            "victim_ip": victim_ip,
            "severity": severity.value,
            "title": title,
            "message": message,
            "probability": probability,
            "prediction_id": prediction_id,
        }
        await ws_manager.broadcast("alerts", payload)
        return {"alert": alert, "severity": severity, "payload": payload}

    def severity_from_probability(self, probability: float) -> str:
        if probability >= SEVERITY_HIGH:
            return "critical"
        if probability >= SEVERITY_MEDIUM:
            return "high"
        if probability >= ALERT_PROB_THRESHOLD:
            return "medium"
        return "low"
