"""Batched GNN training: focal loss, threshold tuning, multi-seed support."""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from typing import Any, Callable

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

from .config import GNN_FOCAL_GAMMA, GNN_USE_FOCAL_LOSS, THRESHOLD_METRIC
from .metrics import find_best_threshold

logger = logging.getLogger(__name__)


class FocalLoss(nn.Module):
    """Focal loss for imbalanced graph labels."""

    def __init__(self, gamma: float = 2.0, weight: torch.Tensor | None = None) -> None:
        super().__init__()
        self.gamma = gamma
        self.weight = weight

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce = F.cross_entropy(logits, targets, weight=self.weight, reduction="none")
        pt = torch.exp(-ce)
        return (((1 - pt) ** self.gamma) * ce).mean()


def _make_loader(graphs: list[Data], batch_size: int, shuffle: bool) -> DataLoader:
    return DataLoader(graphs, batch_size=batch_size, shuffle=shuffle)


def _forward(model: nn.Module, batch: Data) -> torch.Tensor:
    return model(batch.x, batch.edge_index, batch.batch, batch.edge_attr)


def _loss_fn(
    logits: torch.Tensor,
    targets: torch.Tensor,
    class_weights: torch.Tensor | None,
    use_focal: bool,
) -> torch.Tensor:
    w = class_weights.to(logits.device) if class_weights is not None else None
    if use_focal:
        return FocalLoss(GNN_FOCAL_GAMMA, w)(logits, targets)
    return F.cross_entropy(logits, targets, weight=w)


@torch.no_grad()
def predict_graphs(
    model: nn.Module,
    graphs: list[Data],
    device: torch.device,
    batch_size: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    loader = _make_loader(graphs, batch_size, shuffle=False)
    probs, labels = [], []
    for batch in loader:
        batch = batch.to(device)
        logits = _forward(model, batch)
        p = torch.softmax(logits, dim=-1)[:, 1]
        probs.extend(p.cpu().numpy())
        labels.extend(batch.y.cpu().numpy())
    return np.array(labels), np.array(probs)


def tune_threshold(
    model: nn.Module,
    val_graphs: list[Data],
    device: torch.device,
    batch_size: int = 64,
    metric: str = THRESHOLD_METRIC,
) -> tuple[float, float]:
    y_true, y_prob = predict_graphs(model, val_graphs, device, batch_size)
    return find_best_threshold(y_true, y_prob, metric=metric)


@torch.no_grad()
def _eval_loader(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    class_weights: torch.Tensor | None = None,
    threshold: float = 0.5,
    use_focal: bool = GNN_USE_FOCAL_LOSS,
) -> tuple[float, float, float]:
    model.eval()
    all_pred: list[int] = []
    all_true: list[int] = []
    all_prob: list[float] = []
    total_loss = 0.0
    n_batches = 0
    weight = class_weights

    for batch in loader:
        batch = batch.to(device)
        logits = _forward(model, batch)
        loss = _loss_fn(logits, batch.y, weight, use_focal)
        total_loss += loss.item()
        n_batches += 1
        prob = torch.softmax(logits, dim=-1)[:, 1]
        pred = (prob >= threshold).long()
        all_pred.extend(pred.cpu().tolist())
        all_true.extend(batch.y.cpu().tolist())
        all_prob.extend(prob.cpu().tolist())

    if n_batches == 0:
        return 0.0, 0.0, 0.0

    acc = sum(int(p == t) for p, t in zip(all_pred, all_true)) / len(all_true)
    f1s = []
    for c in (0, 1):
        tp = sum(1 for p, t in zip(all_pred, all_true) if p == c and t == c)
        fp = sum(1 for p, t in zip(all_pred, all_true) if p == c and t != c)
        fn = sum(1 for p, t in zip(all_pred, all_true) if p != c and t == c)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    macro_f1 = sum(f1s) / len(f1s)
    return total_loss / n_batches, acc, macro_f1


def train_gnn_batched(
    model: nn.Module,
    train_graphs: list[Data],
    val_graphs: list[Data],
    device: torch.device,
    class_weights: torch.Tensor,
    batch_size: int = 64,
    epochs: int = 80,
    lr: float = 1e-3,
    weight_decay: float = 5e-4,
    patience: int = 12,
    use_focal: bool = GNN_USE_FOCAL_LOSS,
) -> dict[str, list[float]]:
    model = model.to(device)
    train_loader = _make_loader(train_graphs, batch_size, shuffle=True)
    val_loader = _make_loader(val_graphs, batch_size, shuffle=False)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    history: dict[str, list[float]] = {"train_loss": [], "val_loss": [], "val_acc": [], "val_f1": []}
    best_f1 = -1.0
    best_state = None
    stale = 0

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            logits = _forward(model, batch)
            loss = _loss_fn(logits, batch.y, class_weights, use_focal)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        train_loss = epoch_loss / max(n_batches, 1)
        val_loss, val_acc, val_f1 = _eval_loader(
            model, val_loader, device, class_weights, threshold=0.5, use_focal=use_focal
        )
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        history["val_f1"].append(val_f1)

        if epoch % 10 == 0 or epoch == 1:
            logger.info(
                "Epoch %03d | train=%.4f val=%.4f acc=%.4f f1=%.4f",
                epoch, train_loss, val_loss, val_acc, val_f1,
            )

        if val_f1 > best_f1:
            best_f1 = val_f1
            best_state = deepcopy(model.state_dict())
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                logger.info("Early stop epoch %d best_f1=%.4f", epoch, best_f1)
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return history


@torch.no_grad()
def inference_latency_ms(
    model: nn.Module,
    graphs: list[Data],
    device: torch.device,
    batch_size: int = 32,
    runs: int = 30,
) -> float:
    if not graphs:
        return 0.0
    model.eval()
    loader = _make_loader(graphs[: min(256, len(graphs))], batch_size=batch_size, shuffle=False)
    for batch in loader:
        batch = batch.to(device)
        _forward(model, batch)
        break
    if device.type == "cuda":
        torch.cuda.synchronize()

    n_graphs = 0
    start = time.perf_counter()
    for _ in range(runs):
        for batch in loader:
            batch = batch.to(device)
            _forward(model, batch)
            n_graphs += batch.num_graphs
    if device.type == "cuda":
        torch.cuda.synchronize()
    return (time.perf_counter() - start) / max(n_graphs, 1) * 1000


def hyperparameter_grid_batched(
    model_factory: Callable[..., nn.Module],
    train_graphs: list[Data],
    val_graphs: list[Data],
    device: torch.device,
    class_weights: torch.Tensor,
    in_channels: int,
    param_grid: list[dict[str, Any]],
    batch_size: int = 64,
) -> tuple[nn.Module, dict[str, Any], dict[str, list[float]]]:
    best_model, best_params, best_history = None, {}, {}
    best_f1 = -1.0
    for params in param_grid:
        logger.info("Tuning: %s", params)
        kw = {k: v for k, v in params.items() if k in ("hidden_channels", "num_layers", "dropout", "heads")}
        model = model_factory(in_channels=in_channels, out_channels=2, **kw)
        history = train_gnn_batched(
            model, train_graphs, val_graphs, device, class_weights,
            batch_size=batch_size, epochs=params.get("epochs", 35),
            lr=params.get("lr", 1e-3), patience=params.get("patience", 8),
        )
        val_f1 = max(history["val_f1"]) if history["val_f1"] else 0.0
        if val_f1 > best_f1:
            best_f1, best_model, best_params, best_history = val_f1, model, params, history
    assert best_model is not None
    return best_model, best_params, best_history


def train_gnn(*args, **kwargs):
    return train_gnn_batched(*args, **kwargs)
