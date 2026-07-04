"""Alert management endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from ...core.dependencies import get_db, require_roles
from ...db.models import UserRole
from ...db.repositories.alert_repository import AlertRepository
from ...schemas.alerts import AlertAckRequest, AlertResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    limit: int = 50,
    unacknowledged_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    repo = AlertRepository(db)
    rows = await repo.list_recent(limit=limit, unacknowledged_only=unacknowledged_only)
    return [AlertResponse.model_validate(r) for r in rows]


@router.post("/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    body: AlertAckRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst)),
):
    repo = AlertRepository(db)
    alert = await repo.acknowledge(body.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    logger.info("Alert acknowledged id=%s", body.alert_id)
    return AlertResponse.model_validate(alert)
