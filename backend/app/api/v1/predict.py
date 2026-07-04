"""Prediction endpoints."""

import logging

from fastapi import APIRouter, Depends

from ...core.dependencies import get_current_user, get_db
from ...db.models import UserRole
from ...core.dependencies import require_roles
from ...schemas.predict import PredictRequest, PredictResponse
from ...services.detection_service import detection_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["Detection"])


@router.post("", response_model=PredictResponse)
async def predict(
    body: PredictRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    logger.info("Predict request user=%s model=%s flows=%d", user.email, body.model, len(body.flows))
    return await detection_service.predict(db, body)
