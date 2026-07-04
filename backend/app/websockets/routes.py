"""WebSocket channels for real-time streaming."""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.inference_engine import inference_engine
from ..services.metrics_service import MetricsService
from .manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSockets"])


async def _metrics_stream(websocket: WebSocket) -> None:
    """Periodic system metrics push (streaming pipeline)."""
    inference_engine.load_models()
    while True:
        payload = {
            "type": "heartbeat",
            "ts": datetime.now(timezone.utc).isoformat(),
            "models_loaded": inference_engine._loaded,
        }
        await websocket.send_json(payload)
        await asyncio.sleep(5)


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await ws_manager.connect("alerts", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("alerts", websocket)


@router.websocket("/ws/graph")
async def ws_graph(websocket: WebSocket):
    await ws_manager.connect("graph", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("graph", websocket)


@router.websocket("/ws/traffic")
async def ws_traffic(websocket: WebSocket):
    await ws_manager.connect("traffic", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("traffic", websocket)


@router.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket):
    await ws_manager.connect("metrics", websocket)
    try:
        await _metrics_stream(websocket)
    except WebSocketDisconnect:
        await ws_manager.disconnect("metrics", websocket)


@router.websocket("/ws/mitigation")
async def ws_mitigation(websocket: WebSocket):
    await ws_manager.connect("mitigation", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("mitigation", websocket)
