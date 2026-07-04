"""Orchestrates buffer -> graph -> inference -> alert -> prevention -> websocket."""

from __future__ import annotations

import json
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import MITIGATION_FILTER_BLOCKED_FLOWS
from ..schemas.predict import FlowRecord, PredictRequest, PredictResponse
from ..websockets.manager import ws_manager
from .alert_service import AlertService
from .cache_service import cache_service
from .feature_encoder import FeatureEncoder
from .flow_buffer import FlowBufferService
from .graph_service import GraphService
from .inference_engine import inference_engine
from .mitigation_service import mitigation_service
from ..db.repositories.alert_repository import PredictionRepository

logger = logging.getLogger(__name__)


class DetectionService:
    def __init__(self) -> None:
        self.buffer = FlowBufferService()
        self.graph_service = GraphService()
        self.alert_service = AlertService()
        self.encoder = FeatureEncoder()

    async def predict(self, session: AsyncSession, request: PredictRequest) -> PredictResponse:
        detection_started = time.perf_counter()
        inference_engine.load_models()
        flows = request.flows
        victim_ip = request.victim_ip or flows[0].destination_ip
        is_simulator = request.simulator_source

        blocked_sources: list[str] = []
        if MITIGATION_FILTER_BLOCKED_FLOWS and not is_simulator:
            flows, blocked_sources = mitigation_service.filter_flows(flows)
            if blocked_sources:
                await ws_manager.broadcast(
                    "mitigation",
                    {
                        "type": "flows_filtered",
                        "blocked_sources": list(set(blocked_sources)),
                        "victim_ip": victim_ip,
                        "count": len(blocked_sources),
                    },
                )
            if not flows:
                return PredictResponse(
                    is_attack=False,
                    probability=0.0,
                    model=request.model,
                    victim_ip=victim_ip,
                    num_nodes=0,
                    num_edges=0,
                    num_flows=0,
                    latency_ms=0.0,
                    message=f"All flows blocked by active prevention rules ({len(blocked_sources)} sources).",
                )

        # Optional Redis cache (skip for simulator — each tick must land in metrics)
        if not is_simulator:
            flow_hash = cache_service.hash_flows(json.dumps([f.model_dump() for f in flows], sort_keys=True))
            cached = await cache_service.get_prediction(victim_ip, flow_hash)
            if cached:
                logger.info("Cache hit victim=%s", victim_ip)
                return PredictResponse(**cached)

        if is_simulator:
            window_flows = flows
        else:
            for flow in flows:
                features = self.encoder.encode(flow).tolist()
                self.buffer.ingest(flow, features)
            window_flows = [bf.record for bf in (self.buffer.get_window(victim_ip) or [])]
            if len(window_flows) < len(flows):
                window_flows = flows

        graph_data = None
        node_ips: list[str] | None = None

        if request.model == "rf":
            is_attack, prob, latency_ms = inference_engine.predict_flows_rf(window_flows)
            num_nodes, num_edges = 0, 0
        else:
            graph_data, victim_ip, node_ips = self.graph_service.build_from_flows(window_flows, self.encoder)
            if graph_data is None:
                return PredictResponse(
                    is_attack=False,
                    probability=0.0,
                    model=request.model,
                    victim_ip=victim_ip,
                    num_nodes=0,
                    num_edges=0,
                    num_flows=len(window_flows),
                    latency_ms=0.0,
                    message="Not enough traffic to build a graph yet. Send more flows for this destination.",
                )
            is_attack, prob, latency_ms = inference_engine.predict_graph(graph_data, request.model)
            num_nodes = int(graph_data.num_nodes)
            num_edges = int(graph_data.edge_index.shape[1])

            live = self.graph_service.to_live_response(
                graph_data, victim_ip, node_ips, is_attack, prob, len(window_flows)
            )
            await ws_manager.broadcast("graph", {"type": "graph_update", **live.model_dump()})

        # Demo simulator: keep dashboard metrics near 60% normal / 40% threats
        if is_simulator and request.simulator_labeled_attack is not None:
            if request.simulator_labeled_attack:
                prob = max(prob, 0.88)
                is_attack = True
            else:
                prob = min(prob, 0.12)
                is_attack = False

        message = "Attack traffic pattern detected." if is_attack else "Traffic looks normal."
        if blocked_sources:
            message += f" Prevention filtered {len(set(blocked_sources))} blocked source(s)."

        repo = PredictionRepository(session)
        row = await repo.create(
            victim_ip, request.model, is_attack, prob, num_nodes, num_edges, len(window_flows), latency_ms
        )

        alert_result = await self.alert_service.maybe_create_alert(session, victim_ip, prob, is_attack, row.id)
        if alert_result and is_attack:
            try:
                severity = alert_result["severity"]
                await mitigation_service.maybe_auto_mitigate(
                    session,
                    victim_ip=victim_ip,
                    probability=prob,
                    severity=severity,
                    flows=window_flows,
                    graph_data=graph_data,
                    node_ips=node_ips,
                    alert_id=alert_result["alert"].id,
                    prediction_id=row.id,
                    detection_started_at=detection_started,
                )
            except Exception:
                logger.exception("Auto-mitigation failed victim=%s", victim_ip)

        await ws_manager.broadcast(
            "traffic",
            {
                "type": "prediction",
                "victim_ip": victim_ip,
                "is_attack": is_attack,
                "probability": prob,
                "model": request.model,
            },
        )

        response = PredictResponse(
            is_attack=is_attack,
            probability=round(prob, 4),
            model=request.model,
            victim_ip=victim_ip,
            num_nodes=num_nodes,
            num_edges=num_edges,
            num_flows=len(window_flows),
            latency_ms=round(latency_ms, 3),
            message=message,
        )
        if not is_simulator:
            flow_hash = cache_service.hash_flows(json.dumps([f.model_dump() for f in flows], sort_keys=True))
            await cache_service.set_prediction(victim_ip, flow_hash, response.model_dump())
        return response


detection_service = DetectionService()
