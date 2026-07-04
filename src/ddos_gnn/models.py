"""GCN and GAT graph-level classifiers with edge-weighted message passing."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn
from torch_geometric.nn import GATConv, GCNConv, global_max_pool, global_mean_pool


def _edge_weight(edge_attr: torch.Tensor | None, num_edges: int, device: torch.device) -> torch.Tensor | None:
    if edge_attr is None or edge_attr.numel() == 0:
        return None
    w = edge_attr.view(-1).to(device)
    if w.shape[0] != num_edges:
        return None
    w = w - w.min()
    return w / (w.max() + 1e-6) if w.max() > 0 else torch.ones_like(w)


class GCNGraphClassifier(nn.Module):
    """Edge-weighted GCN + mean/max pooling + MLP head."""

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 64,
        out_channels: int = 2,
        num_layers: int = 3,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.dropout = dropout
        self.convs = nn.ModuleList()
        self.convs.append(GCNConv(in_channels, hidden_channels))
        for _ in range(num_layers - 2):
            self.convs.append(GCNConv(hidden_channels, hidden_channels))
        self.convs.append(GCNConv(hidden_channels, hidden_channels))
        self.head = nn.Sequential(
            nn.Linear(hidden_channels * 2, hidden_channels),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels, out_channels),
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
        edge_attr: torch.Tensor | None = None,
    ) -> torch.Tensor:
        ew = _edge_weight(edge_attr, edge_index.shape[1], x.device)
        for conv in self.convs:
            x = conv(x, edge_index, edge_weight=ew)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        g = torch.cat([global_mean_pool(x, batch), global_max_pool(x, batch)], dim=-1)
        return self.head(g)


class GATGraphClassifier(nn.Module):
    """GAT with edge_dim=1 (packet-rate on edges) + pooling head."""

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 48,
        out_channels: int = 2,
        heads: int = 4,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.dropout = dropout
        self.gat1 = GATConv(
            in_channels, hidden_channels, heads=heads, dropout=dropout, edge_dim=1
        )
        self.gat2 = GATConv(
            hidden_channels * heads,
            hidden_channels,
            heads=1,
            concat=False,
            dropout=dropout,
            edge_dim=1,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_channels * 2, hidden_channels),
            nn.ELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels, out_channels),
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
        edge_attr: torch.Tensor | None = None,
    ) -> torch.Tensor:
        ea = edge_attr if edge_attr is not None else torch.ones(edge_index.shape[1], 1, device=x.device)
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.gat1(x, edge_index, edge_attr=ea)
        x = F.elu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.gat2(x, edge_index, edge_attr=ea)
        g = torch.cat([global_mean_pool(x, batch), global_max_pool(x, batch)], dim=-1)
        return self.head(g)


# Legacy node-level (kept for compatibility)
class GCNClassifier(GCNGraphClassifier):
    def forward(self, x, edge_index, batch=None, edge_attr=None):
        if batch is None:
            batch = torch.zeros(x.size(0), dtype=torch.long, device=x.device)
        return super().forward(x, edge_index, batch, edge_attr)


class GATClassifier(GATGraphClassifier):
    pass
