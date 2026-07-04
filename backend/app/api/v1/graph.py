"""Live graph endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from ...core.dependencies import get_db, require_roles
from ...db.models import UserRole
from ...schemas.graph import LiveGraphResponse
from ...services.detection_service import detection_service
from ...services.graph_service import GraphService
from ...services.inference_engine import inference_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/live/{victim_ip}", response_model=LiveGraphResponse)
async def live_graph(
    victim_ip: str,
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    window = detection_service.buffer.get_window(victim_ip)
    if not window:
        raise HTTPException(status_code=404, detail="No buffered traffic for this destination yet")

    flows = [bf.record for bf in window]
    inference_engine.load_models()
    graph_svc = GraphService()
    data, victim, ips = graph_svc.build_from_flows(flows, detection_service.encoder)
    if data is None:
        raise HTTPException(status_code=400, detail="Could not build graph from buffer")

    is_attack, prob, _ = inference_engine.predict_graph(data, "gcn")
    return graph_svc.to_live_response(data, victim, ips, is_attack, prob, len(flows))


@router.get("/victims")
async def list_victims(
    _user=Depends(require_roles(UserRole.admin, UserRole.analyst, UserRole.viewer)),
):
    return {"victims": detection_service.buffer.victim_ips()}
