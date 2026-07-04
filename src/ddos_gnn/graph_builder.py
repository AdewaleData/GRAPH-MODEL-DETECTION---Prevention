"""Graph construction with NetworkX and PyTorch Geometric."""

from __future__ import annotations

import logging
from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch_geometric.data import Data

from .config import RANDOM_SEED
from .data_loader import binary_labels

logger = logging.getLogger(__name__)

SRC_COL = "Source IP"
DST_COL = "Destination IP"


class IPNodeIndexer:
    """
    Hash map: IP string -> contiguous node index.
    DSA: O(1) average insert/lookup via dict.
    """

    def __init__(self) -> None:
        self._map: dict[str, int] = {}
        self._reverse: list[str] = []

    def get_or_create(self, ip: str) -> int:
        if ip not in self._map:
            self._map[ip] = len(self._reverse)
            self._reverse.append(ip)
        return self._map[ip]

    def __len__(self) -> int:
        return len(self._reverse)

    @property
    def ips(self) -> list[str]:
        return self._reverse


def build_communication_graph(
    df: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[nx.DiGraph, IPNodeIndexer, np.ndarray, np.ndarray, torch.Tensor, torch.Tensor]:
    """
  Build directed graph from flows.
    - Nodes: IPs (hash map indexing)
    - Edges: src -> dst per flow
    - Node features: mean of incident flow feature vectors (matrix aggregation)
    - Node labels: 1 if majority of incident flows are attacks
    """
    indexer = IPNodeIndexer()
    y_flow = binary_labels(df["Label"])

    node_sums = defaultdict(lambda: np.zeros(len(feature_cols), dtype=np.float64))
    node_counts: dict[int, int] = defaultdict(int)
    node_attack: dict[int, int] = defaultdict(int)

    edges_src: list[int] = []
    edges_dst: list[int] = []
    edge_weights: list[float] = []

    feat_matrix = df[feature_cols].values.astype(np.float64)
    packets_col = "Flow Packets/s"
    packets = df[packets_col].values if packets_col in df.columns else np.ones(len(df))

    G = nx.DiGraph()

    for i in range(len(df)):
        row = df.iloc[i]
        src = str(row[SRC_COL])
        dst = str(row[DST_COL])
        u = indexer.get_or_create(src)
        v = indexer.get_or_create(dst)
        feat = feat_matrix[i]

        node_sums[u] += feat
        node_sums[v] += feat
        node_counts[u] += 1
        node_counts[v] += 1
        if y_flow[i]:
            node_attack[u] += 1
            node_attack[v] += 1

        edges_src.append(u)
        edges_dst.append(v)
        edge_weights.append(float(packets[i]))
        G.add_edge(u, v, flow_idx=i, attack=int(y_flow[i]))

    num_nodes = len(indexer)
    x = np.zeros((num_nodes, len(feature_cols)), dtype=np.float32)
    y_node = np.zeros(num_nodes, dtype=np.int64)

    for nid in range(num_nodes):
        cnt = max(node_counts.get(nid, 1), 1)
        x[nid] = (node_sums[nid] / cnt).astype(np.float32)
        y_node[nid] = 1 if node_attack.get(nid, 0) > cnt / 2 else 0

    edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
    edge_attr = torch.tensor(edge_weights, dtype=torch.float32).view(-1, 1)

    logger.info(
        "Graph built: nodes=%d edges=%d | NetworkX edges=%d",
        num_nodes,
        edge_index.shape[1],
        G.number_of_edges(),
    )
    return G, indexer, x, y_node, edge_index, edge_attr


def build_pyg_data(
    x: np.ndarray,
    y_node: np.ndarray,
    edge_index: torch.Tensor,
    edge_attr: torch.Tensor,
) -> Data:
    """Package tensors into PyG Data with train/val/test masks."""
    x_t = torch.tensor(x, dtype=torch.float32)
    y_t = torch.tensor(y_node, dtype=torch.long)
    train_mask, val_mask, test_mask = _node_masks(y_node)

    data = Data(
        x=x_t,
        edge_index=edge_index,
        edge_attr=edge_attr,
        y=y_t,
        train_mask=train_mask,
        val_mask=val_mask,
        test_mask=test_mask,
    )
    data.num_nodes = x_t.shape[0]
    return data


def _can_stratify(y: np.ndarray) -> bool:
    """Stratified split needs >=2 samples per class."""
    _, counts = np.unique(y, return_counts=True)
    return bool(np.all(counts >= 2))


def _node_masks(y: np.ndarray) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Boolean masks over nodes; stratified when class counts allow."""
    indices = np.arange(len(y))
    strat = y if _can_stratify(y) else None
    train_idx, temp_idx = train_test_split(
        indices, test_size=0.30, stratify=strat, random_state=RANDOM_SEED
    )
    y_temp = y[temp_idx]
    strat_temp = y_temp if _can_stratify(y_temp) else None
    val_idx, test_idx = train_test_split(
        temp_idx, test_size=0.50, stratify=strat_temp, random_state=RANDOM_SEED
    )

    def mask_from(idxs: np.ndarray, n: int) -> torch.Tensor:
        m = torch.zeros(n, dtype=torch.bool)
        m[torch.tensor(idxs, dtype=torch.long)] = True
        return m

    n = len(y)
    return mask_from(train_idx, n), mask_from(val_idx, n), mask_from(test_idx, n)


def bfs_layers(G: nx.DiGraph, source: int, max_depth: int = 3) -> list[list[int]]:
    """BFS layering — O(V + E) for sparse graphs."""
    visited = {source}
    layers: list[list[int]] = [[source]]
    frontier = [source]
    for _ in range(max_depth):
        next_frontier: list[int] = []
        for u in frontier:
            for v in G.successors(u):
                if v not in visited:
                    visited.add(v)
                    next_frontier.append(v)
        if not next_frontier:
            break
        layers.append(next_frontier)
        frontier = next_frontier
    return layers


def dfs_attack_region(G: nx.DiGraph, max_nodes: int = 50) -> list[int]:
    """DFS from hub node — stack-based O(V) traversal cap."""
    if G.number_of_nodes() == 0:
        return []
    start = max(G.degree, key=lambda t: t[1])[0]
    stack = [start]
    visited: set[int] = set()
    order: list[int] = []
    while stack and len(order) < max_nodes:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        order.append(u)
        stack.extend(list(G.successors(u))[:5])
    return order


def subgraph_for_viz(G: nx.DiGraph, max_nodes: int = 80) -> nx.DiGraph:
    """Extract small subgraph via BFS from highest-degree node."""
    if G.number_of_nodes() <= max_nodes:
        return G.copy()
    hub = max(G.degree, key=lambda t: t[1])[0]
    layers = bfs_layers(G, hub, max_depth=4)
    nodes = {n for layer in layers for n in layer}
    nodes_list = list(nodes)[:max_nodes]
    return G.subgraph(nodes_list).copy()
