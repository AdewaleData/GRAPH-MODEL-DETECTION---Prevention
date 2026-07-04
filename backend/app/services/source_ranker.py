"""Rank attacker source IPs from flow windows and attack graphs."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from torch_geometric.data import Data

from ..schemas.predict import FlowRecord


def rank_attacker_sources(
    flows: list[FlowRecord],
    victim_ip: str,
    graph_data: Data | None = None,
    node_ips: list[str] | None = None,
    top_k: int = 10,
) -> list[tuple[str, float, dict]]:
    """
    Return [(source_ip, score, metadata), ...] sorted descending.
    Combines flow volume signals with graph topology when available.
    """
    flow_scores: dict[str, float] = defaultdict(float)
    flow_meta: dict[str, dict] = defaultdict(lambda: {"flows": 0, "packets_s": 0.0, "syn_flags": 0})

    for flow in flows:
        src = flow.source_ip
        if src == victim_ip:
            continue
        weight = float(flow.flow_packets_s or 0) + float(flow.flow_bytes_s or 0) / 1e6
        weight += float(flow.syn_flag_count or 0) * 2.0
        flow_scores[src] += weight
        flow_meta[src]["flows"] += 1
        flow_meta[src]["packets_s"] += float(flow.flow_packets_s or 0)
        flow_meta[src]["syn_flags"] += int(flow.syn_flag_count or 0)

    if graph_data is not None and node_ips:
        _boost_from_graph(graph_data, node_ips, victim_ip, flow_scores, flow_meta)

    ranked = sorted(flow_scores.items(), key=lambda x: x[1], reverse=True)
    return [(ip, score, dict(flow_meta[ip])) for ip, score in ranked[:top_k]]


def _boost_from_graph(
    graph_data: Data,
    node_ips: list[str],
    victim_ip: str,
    scores: dict[str, float],
    meta: dict[str, dict],
) -> None:
    """Boost scores using node degree and outbound edge weights."""
    ip_to_idx = {ip: i for i, ip in enumerate(node_ips)}
    victim_idx = ip_to_idx.get(victim_ip)

    ei = graph_data.edge_index.cpu().numpy()
    ew = graph_data.edge_attr.view(-1).cpu().numpy() if graph_data.edge_attr is not None else np.ones(ei.shape[1])

    outbound: dict[int, float] = defaultdict(float)
    for j in range(ei.shape[1]):
        src_idx, dst_idx = int(ei[0, j]), int(ei[1, j])
        if victim_idx is not None and dst_idx == victim_idx:
            outbound[src_idx] += float(ew[j])

    n_feat = graph_data.x.shape[1]
    extra = 3
    base_feat = n_feat - extra if n_feat > extra else n_feat

    for ip, idx in ip_to_idx.items():
        if ip == victim_ip or idx >= graph_data.num_nodes:
            continue
        x = graph_data.x[idx]
        degree = float(x[base_feat + 2].item()) if base_feat + 2 < n_feat else 0.0
        graph_boost = degree * 0.5 + outbound.get(idx, 0.0)
        scores[ip] = scores.get(ip, 0.0) + graph_boost
        if ip in meta:
            meta[ip]["graph_degree"] = round(degree, 2)
            meta[ip]["outbound_weight"] = round(outbound.get(idx, 0.0), 2)
