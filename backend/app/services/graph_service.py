"""Dynamic graph construction for live inference."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import torch
from torch_geometric.data import Data

# ML package on path
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from ddos_gnn.graph_dataset import _build_window_graph  # noqa: E402

from ..schemas.graph import GraphEdge, GraphNode, LiveGraphResponse
from ..schemas.predict import FlowRecord
from .feature_encoder import FeatureEncoder

logger = logging.getLogger(__name__)


class GraphService:
    def build_pyg_graph(
        self,
        flows: list[FlowRecord],
        feature_matrix: np.ndarray,
    ) -> tuple[Data | None, str]:
        if len(flows) < 2:
            return None, flows[0].destination_ip if flows else "unknown"

        victim_ip = flows[0].destination_ip
        src_ips = np.array([f.source_ip for f in flows], dtype=object)
        dst_ips = np.array([f.destination_ip for f in flows], dtype=object)
        y_dummy = np.zeros(len(flows), dtype=np.int64)
        packets = np.array([f.flow_packets_s for f in flows], dtype=np.float32)
        indices = list(range(len(flows)))

        data = _build_window_graph(indices, src_ips, dst_ips, feature_matrix, y_dummy, victim_ip, packets)
        return data, victim_ip

    def to_live_response(
        self,
        data: Data,
        victim_ip: str,
        indexer_ips: list[str] | None = None,
        is_attack: bool | None = None,
        probability: float | None = None,
        num_flows: int = 0,
    ) -> LiveGraphResponse:
        """Serialize PyG graph for API / WebSocket clients."""
        nodes: list[GraphNode] = []
        n_feat = data.x.shape[1]
        extra = 3
        base_feat = n_feat - extra if n_feat > extra else n_feat

        # Reconstruct IP list from stored metadata or placeholders
        ips = indexer_ips or [f"node_{i}" for i in range(data.num_nodes)]

        for i in range(data.num_nodes):
            x = data.x[i]
            nodes.append(
                GraphNode(
                    id=i,
                    ip=ips[i] if i < len(ips) else f"node_{i}",
                    is_victim=float(x[base_feat].item()) > 0.5 if base_feat < n_feat else False,
                    is_source=float(x[base_feat + 1].item()) > 0.5 if base_feat + 1 < n_feat else False,
                    degree=float(x[base_feat + 2].item()) if base_feat + 2 < n_feat else 0.0,
                )
            )

        edges: list[GraphEdge] = []
        ei = data.edge_index.cpu().numpy()
        ew = data.edge_attr.view(-1).cpu().tolist() if data.edge_attr is not None else [1.0] * ei.shape[1]
        for j in range(ei.shape[1]):
            edges.append(GraphEdge(source=int(ei[0, j]), target=int(ei[1, j]), weight=float(ew[j])))

        return LiveGraphResponse(
            victim_ip=victim_ip,
            nodes=nodes,
            edges=edges,
            is_attack=is_attack,
            probability=probability,
            num_flows=num_flows or data.num_edges,
        )

    def build_from_flows(self, flows: list[FlowRecord], encoder: FeatureEncoder) -> tuple[Data | None, str, list[str]]:
        matrix = encoder.encode_batch(flows)
        data, victim = self.build_pyg_graph(flows, matrix)
        ips = list({f.source_ip for f in flows} | {f.destination_ip for f in flows})  # noqa: set union
        return data, victim, ips
