"""Health check."""

from fastapi import APIRouter, Response

from ...core.config import APP_NAME, APP_VERSION, PRODUCTION
from ...services.inference_engine import inference_engine

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health(response: Response):
    inference_engine.load_models()
    models = {
        "gcn": inference_engine.gcn is not None,
        "gat": inference_engine.gat is not None,
        "rf": inference_engine.rf_bundle is not None,
    }
    any_model = any(models.values())
    status = "healthy" if any_model else "degraded"
    if PRODUCTION and not any_model:
        response.status_code = 503
        status = "unhealthy"
    return {
        "status": status,
        "service": APP_NAME,
        "version": APP_VERSION,
        "production": PRODUCTION,
        "models": models,
    }
