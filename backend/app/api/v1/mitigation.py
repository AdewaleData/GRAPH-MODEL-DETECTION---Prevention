"""Prevention / mitigation management endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_db, require_roles
from ...db.models import MitigationActionType, UserRole
from ...db.repositories.mitigation_repository import MitigationRepository
from ...schemas.mitigation import (
    BlocklistResponse,
    MitigationApplyRequest,
    MitigationRecordResponse,
    MitigationRevokeRequest,
    MitigationSummary,
    PreventionStatsResponse,
)
from ...services.blocklist_service import blocklist_service
from ...services.mitigation_service import mitigation_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mitigation", tags=["Prevention"])


@router.get("/active", response_model=list[MitigationRecordResponse])
async def list_active_mitigations(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    repo = MitigationRepository(db)
    rows = await repo.list_active(limit=limit)
    return [MitigationRecordResponse.model_validate(r) for r in rows]


@router.get("/history", response_model=list[MitigationRecordResponse])
async def mitigation_history(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    repo = MitigationRepository(db)
    rows = await repo.list_recent(limit=limit)
    return [MitigationRecordResponse.model_validate(r) for r in rows]


@router.get("/summary", response_model=MitigationSummary)
async def mitigation_summary(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    data = await mitigation_service.summary(db)
    return MitigationSummary(**data)


@router.get("/blocklist", response_model=BlocklistResponse)
async def get_blocklist(
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    stats = blocklist_service.stats
    return BlocklistResponse(
        blocked=blocklist_service.entries(MitigationActionType.block),
        rate_limited=blocklist_service.entries(MitigationActionType.rate_limit),
        quarantined=blocklist_service.entries(MitigationActionType.quarantine),
        stats=stats,
    )


@router.get("/stats", response_model=PreventionStatsResponse)
async def prevention_stats(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    summary = await mitigation_service.summary(db)
    ps = mitigation_service.prevention_stats
    return PreventionStatsResponse(
        flows_blocked=ps["flows_blocked"],
        flows_allowed=ps["flows_allowed"],
        mitigation_summary=MitigationSummary(**summary),
    )


@router.post("/apply", response_model=MitigationRecordResponse)
async def apply_mitigation(
    body: MitigationApplyRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst)),
):
    try:
        action = MitigationActionType(body.action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {body.action}") from None

    result = await mitigation_service.apply_manual(
        db, body.source_ip, body.victim_ip, action, body.reason
    )
    record_id = result["id"]
    repo = MitigationRepository(db)
    record = await repo.get(record_id)
    logger.info("Manual mitigation source=%s action=%s", body.source_ip, action.value)
    return MitigationRecordResponse.model_validate(record)


@router.post("/revoke", response_model=list[MitigationRecordResponse])
async def revoke_mitigation(
    body: MitigationRevokeRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst)),
):
    if not body.record_id and not body.source_ip:
        raise HTTPException(status_code=400, detail="Provide record_id or source_ip")
    results = await mitigation_service.revoke(db, record_id=body.record_id, source_ip=body.source_ip)
    if not results:
        raise HTTPException(status_code=404, detail="No active mitigation found")
    repo = MitigationRepository(db)
    out = []
    for r in results:
        record = await repo.get(r["id"])
        if record:
            out.append(MitigationRecordResponse.model_validate(record))
    return out
