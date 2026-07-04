"""
Batched flow-window graph dataset — production graph construction.

DSA: hash map grouping O(n), adjacency via COO edge_index, sliding windows with cap.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch_geometric.data import Data

from .config import (
    GRAPH_EXTRA_NODE_FEATURES,
    GRAPH_GROUP_COL,
    GRAPH_LABEL_MIN_ATTACK_RATIO,
    GRAPH_MAX_FLOWS,
    GRAPH_MAX_PER_VICTIM,
    GRAPH_MIN_FLOWS,
    GRAPH_WINDOW_STRIDE,
    RANDOM_SEED,
    VICTIM_HOLDOUT_RATIO,
)
from .data_loader import binary_labels
from .graph_builder import IPNodeIndexer, build_communication_graph, subgraph_for_viz

logger = logging.getLogger(__name__)

SRC_COL = "Source IP"
DST_COL = "Destination IP"


def _aggregate_edges(
    edges_src: list[int],
    edges_dst: list[int],
    e_attr: list[float],
) -> tuple[list[int], list[int], list[float]]:
    """Merge parallel edges — hash map (u,v) -> (weight_sum, count)."""
    edge_map: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for u, v, w in zip(edges_src, edges_dst, e_attr):
        edge_map[(u, v)][0] += w
        edge_map[(u, v)][1] += 1.0
    new_src, new_dst, new_attr = [], [], []
    for (u, v), (wsum, cnt) in edge_map.items():
        new_src.append(u)
        new_dst.append(v)
        new_attr.append(wsum / max(cnt, 1.0))
    return new_src, new_dst, new_attr


def _build_window_graph(
    flow_indices: list[int],
    src_ips: np.ndarray,
    dst_ips: np.ndarray,
    feat_matrix: np.ndarray,
    y_flow: np.ndarray,
    victim_ip: str,
    edge_weights: np.ndarray | None = None,
) -> Data | None:
    indexer = IPNodeIndexer()
    n_feat = feat_matrix.shape[1]
    extra = GRAPH_EXTRA_NODE_FEATURES

    node_sum = defaultdict(lambda: np.zeros(n_feat, dtype=np.float32))
    node_cnt: dict[int, int] = defaultdict(int)
    out_degree: dict[int, int] = defaultdict(int)
    in_degree: dict[int, int] = defaultdict(int)
    edges_src: list[int] = []
    edges_dst: list[int] = []
    e_attr: list[float] = []

    for idx in flow_indices:
        src = str(src_ips[idx])
        dst = str(dst_ips[idx])
        u = indexer.get_or_create(src)
        v = indexer.get_or_create(dst)
        f = feat_matrix[idx]
        node_sum[u] += f
        node_sum[v] += f
        node_cnt[u] += 1
        node_cnt[v] += 1
        out_degree[u] += 1
        in_degree[v] += 1
        w = float(edge_weights[idx]) if edge_weights is not None else 1.0
        edges_src.append(u)
        edges_dst.append(v)
        e_attr.append(w)

    n_nodes = len(indexer)
    if n_nodes < 2 or len(edges_src) < 2:
        return None

    edges_src, edges_dst, e_attr = _aggregate_edges(edges_src, edges_dst, e_attr)

    victim_id = indexer._map.get(victim_ip, -1)
    x = np.zeros((n_nodes, n_feat + extra), dtype=np.float32)
    for nid in range(n_nodes):
        c = max(node_cnt[nid], 1)
        x[nid, :n_feat] = node_sum[nid] / c
        ip = indexer.ips[nid]
        x[nid, n_feat] = 1.0 if ip == victim_ip or nid == victim_id else 0.0
        x[nid, n_feat + 1] = 1.0 if out_degree[nid] > 0 else 0.0
        deg = in_degree[nid] + out_degree[nid]
        x[nid, n_feat + 2] = np.log1p(deg)

    attack_ratio = float(y_flow[flow_indices].mean())
    y_graph = int(attack_ratio >= GRAPH_LABEL_MIN_ATTACK_RATIO)

    edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
    edge_attr = torch.tensor(e_attr, dtype=torch.float32).view(-1, 1)

    data = Data(
        x=torch.from_numpy(x),
        edge_index=edge_index,
        edge_attr=edge_attr,
        y=torch.tensor([y_graph], dtype=torch.long),
        num_nodes=n_nodes,
        num_edges=len(edges_src),
        attack_ratio=attack_ratio,
        flow_indices=torch.tensor(flow_indices, dtype=torch.long),
        victim_ip=victim_ip,
    )
    return data


def _select_windows(indices: list[int], max_flows: int, stride: int, max_per_victim: int) -> list[list[int]]:
    """Cap sliding windows per victim — evenly spaced starts (reduces correlation)."""
    if len(indices) <= max_flows:
        return [indices]
    starts = list(range(0, len(indices) - max_flows + 1, stride))
    if len(starts) > max_per_victim:
        step = max(1, len(starts) // max_per_victim)
        starts = starts[::step][:max_per_victim]
    return [indices[s : s + max_flows] for s in starts]


def build_flow_graphs(
    df: pd.DataFrame,
    feat_matrix: np.ndarray,
    y_flow: np.ndarray | None = None,
    group_col: str = GRAPH_GROUP_COL,
    min_flows: int = GRAPH_MIN_FLOWS,
    max_flows: int = GRAPH_MAX_FLOWS,
    stride: int = GRAPH_WINDOW_STRIDE,
    max_per_victim: int = GRAPH_MAX_PER_VICTIM,
) -> list[Data]:
    y_flow = y_flow if y_flow is not None else binary_labels(df["Label"])
    src_ips = df[SRC_COL].astype(str).values
    dst_ips = df[DST_COL].astype(str).values
    packets = (
        df["Flow Packets/s"].fillna(1.0).values.astype(np.float32)
        if "Flow Packets/s" in df.columns
        else np.ones(len(df), dtype=np.float32)
    )

    groups: dict[str, list[int]] = defaultdict(list)
    for i, key in enumerate(df[group_col].astype(str).values):
        groups[key].append(i)

    graphs: list[Data] = []
    stride = max(1, stride)

    for victim_ip, indices in groups.items():
        if len(indices) < min_flows:
            continue
        for window in _select_windows(indices, max_flows, stride, max_per_victim):
            if len(window) < min_flows:
                continue
            g = _build_window_graph(window, src_ips, dst_ips, feat_matrix, y_flow, victim_ip, packets)
            if g is not None:
                graphs.append(g)

    if graphs:
        labels = [int(g.y.item()) for g in graphs]
        logger.info(
            "Built %d graphs | avg nodes=%.1f edges=%.1f | attack=%d benign=%d",
            len(graphs),
            np.mean([g.num_nodes for g in graphs]),
            np.mean([g.num_edges for g in graphs]),
            sum(labels),
            len(labels) - sum(labels),
        )
    return graphs


def split_flow_indices(
    n: int,
    y_flow: np.ndarray,
    train_ratio: float = 0.70,
    seed: int = RANDOM_SEED,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    idx = np.arange(n)
    strat = y_flow if len(np.unique(y_flow)) > 1 else None
    train_idx, temp_idx = train_test_split(
        idx, test_size=(1 - train_ratio), stratify=strat, random_state=seed
    )
    y_temp = y_flow[temp_idx]
    strat_t = y_temp if len(np.unique(y_temp)) > 1 and np.min(np.bincount(y_temp)) >= 2 else None
    val_idx, test_idx = train_test_split(
        temp_idx, test_size=0.50, stratify=strat_t, random_state=seed
    )
    return train_idx, val_idx, test_idx


def split_victim_holdout(
    df: pd.DataFrame,
    holdout_ratio: float = VICTIM_HOLDOUT_RATIO,
    seed: int = RANDOM_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hold out entire victim IPs for inductive generalization test."""
    victims = df[GRAPH_GROUP_COL].astype(str).unique()
    n_hold = max(1, int(len(victims) * holdout_ratio))
    rng = np.random.default_rng(seed)
    holdout_victims = set(rng.choice(victims, size=n_hold, replace=False))
    mask = df[GRAPH_GROUP_COL].astype(str).isin(holdout_victims)
    test_df = df[mask].reset_index(drop=True)
    train_df = df[~mask].reset_index(drop=True)
    logger.info("Victim hold-out: %d victims, %d test flows", n_hold, len(test_df))
    return train_df, test_df


def build_graph_splits(
    df: pd.DataFrame,
    feat_matrix: np.ndarray,
    train_ratio: float = 0.70,
    seed: int = RANDOM_SEED,
) -> tuple[list[Data], list[Data], list[Data], torch.Tensor]:
    y_flow = binary_labels(df["Label"])
    train_idx, val_idx, test_idx = split_flow_indices(len(df), y_flow, train_ratio, seed)

    def subset(idxs: np.ndarray) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
        return df.iloc[idxs].reset_index(drop=True), feat_matrix[idxs], y_flow[idxs]

    train_g = build_flow_graphs(*subset(train_idx))
    val_g = build_flow_graphs(*subset(val_idx))
    test_g = build_flow_graphs(*subset(test_idx))
    weights = compute_class_weights(train_g)
    logger.info("Graph splits seed=%d: train=%d val=%d test=%d", seed, len(train_g), len(val_g), len(test_g))
    return train_g, val_g, test_g, weights, train_idx, val_idx, test_idx


def aligned_tabular_splits(
    feat_matrix: np.ndarray,
    y_flow: np.ndarray,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
) -> tuple[np.ndarray, ...]:
    """Tabular arrays using the same indices as graph splits."""
    return (
        feat_matrix[train_idx],
        feat_matrix[val_idx],
        feat_matrix[test_idx],
        y_flow[train_idx],
        y_flow[val_idx],
        y_flow[test_idx],
    )


def compute_class_weights(graphs: list[Data]) -> torch.Tensor:
    if not graphs:
        return torch.tensor([1.0, 1.0])
    y = np.array([int(g.y.item()) for g in graphs])
    counts = np.bincount(y, minlength=2).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    weights = len(y) / (len(counts) * counts)
    weights = weights / weights.sum() * len(counts)  # normalize → stable loss scale
    return torch.tensor(weights, dtype=torch.float32)


def map_graph_preds_to_flows(
    graphs: list[Data],
    y_prob: np.ndarray,
    threshold: float,
    n_flows: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Propagate graph-window predictions to member flows (fair flow-level GNN eval)."""
    flow_prob = np.zeros(n_flows, dtype=np.float32)
    flow_count = np.zeros(n_flows, dtype=np.int32)
    for g, p in zip(graphs, y_prob):
        for idx in g.flow_indices.tolist():
            if 0 <= idx < n_flows:
                flow_prob[idx] += p
                flow_count[idx] += 1
    mask = flow_count > 0
    flow_prob[mask] /= flow_count[mask]
    flow_pred = (flow_prob >= threshold).astype(int)
    return flow_pred, flow_prob


def rf_window_baseline(
    graphs: list[Data],
    rf_model: Any,
    scaler: Any,
    feat_matrix: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Graph-level RF baseline: mean flow RF prob per window (fair graph comparison)."""
    probs_g: list[float] = []
    labels_g: list[int] = []
    for g in graphs:
        idxs = g.flow_indices.tolist()
        X = scaler.transform(feat_matrix[idxs])
        p = rf_model.predict_proba(X)[:, 1]
        probs_g.append(float(p.mean()))
        labels_g.append(int(g.y.item()))
    return np.array(labels_g), np.array(probs_g)


def get_viz_graph(df: pd.DataFrame, feature_cols: list[str], max_nodes: int = 80):
    G, indexer, *_ = build_communication_graph(df, feature_cols)
    return subgraph_for_viz(G, max_nodes=max_nodes), indexer
