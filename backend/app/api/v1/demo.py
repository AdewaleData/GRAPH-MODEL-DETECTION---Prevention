"""Demo / simulator status for dashboard diagnostics."""

from fastapi import APIRouter, Depends

from ...core.config import LIVE_SIMULATOR_ENABLED, LIVE_SIMULATOR_INTERVAL_SECONDS, LOAD_GCN, LOAD_GAT, LOAD_RF
from ...core.dependencies import require_roles
from ...db.models import UserRole
from ...services.inference_engine import inference_engine
from ...services.live_simulator import live_simulator

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.get("/status")
async def demo_status(_user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer))):
    inference_engine.load_models()
    return {
        "simulator_enabled": LIVE_SIMULATOR_ENABLED,
        "simulator_running": live_simulator.is_running,
        "traffic_windows": live_simulator.window_count,
        "simulator_interval_seconds": LIVE_SIMULATOR_INTERVAL_SECONDS,
        "models_loaded": inference_engine._loaded,
        "models": {
            "gcn": inference_engine.gcn is not None,
            "gat": inference_engine.gat is not None,
            "rf": inference_engine.rf_bundle is not None,
        },
        "load_flags": {"gcn": LOAD_GCN, "gat": LOAD_GAT, "rf": LOAD_RF},
    }
