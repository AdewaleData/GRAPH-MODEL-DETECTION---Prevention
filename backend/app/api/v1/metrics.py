"""Metrics endpoints."""

from fastapi import APIRouter, Depends

from ...core.dependencies import get_db, require_roles
from ...db.models import UserRole
from ...schemas.metrics import MetricsSummary, PredictionHistoryItem
from ...services.metrics_service import MetricsService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("", response_model=MetricsSummary)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    return await MetricsService().summary(db)


@router.get("/history", response_model=list[PredictionHistoryItem])
async def prediction_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    return await MetricsService().prediction_history(db, limit=limit)
