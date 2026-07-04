"""Model serialization and real-time inference helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import torch
from torch import nn

logger = logging.getLogger(__name__)


def ensure_artifact_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)
        logger.info("Artifact dir ready: %s", p)


def save_sklearn_bundle(path: Path, model: Any, scaler: Any, feature_cols: list[str]) -> None:
    bundle = {"model": model, "scaler": scaler, "feature_cols": feature_cols}
    joblib.dump(bundle, path)
    logger.info("Saved sklearn bundle -> %s", path)


def load_sklearn_bundle(path: Path) -> dict[str, Any]:
    bundle = joblib.load(path)
    logger.info("Loaded sklearn bundle from %s", path)
    return bundle


def predict_flow_sklearn(bundle: dict[str, Any], flow_features: np.ndarray) -> tuple[int, float]:
    """Single-flow inference for backend deployment (tabular)."""
    x = bundle["scaler"].transform(flow_features.reshape(1, -1))
    prob = bundle["model"].predict_proba(x)[0, 1]
    pred = int(prob >= 0.5)
    return pred, float(prob)


def predict_graph_batch(
    model: nn.Module,
    graphs: list[Any],
    device: torch.device,
    batch_size: int = 32,
) -> tuple[list[int], list[float]]:
    """Batch graph inference for streaming flow windows."""
    from torch_geometric.loader import DataLoader

    model.eval()
    loader = DataLoader(graphs, batch_size=batch_size, shuffle=False)
    preds: list[int] = []
    probs: list[float] = []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits = model(batch.x, batch.edge_index, batch.batch, batch.edge_attr)
            prob = torch.softmax(logits, dim=-1)[:, 1]
            preds.extend(logits.argmax(dim=-1).cpu().tolist())
            probs.extend(prob.cpu().tolist())
    return preds, probs


def save_gnn_model(path: Path, model: nn.Module, metadata: dict[str, Any]) -> None:
    torch.save({"state_dict": model.state_dict(), "metadata": metadata}, path)
    meta_path = path.with_suffix(".json")
    meta_path.write_text(json.dumps(metadata, indent=2))
    logger.info("Saved GNN -> %s", path)


def load_gnn_model(path: Path, model: nn.Module) -> dict[str, Any]:
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["state_dict"])
    logger.info("Loaded GNN from %s", path)
    return ckpt.get("metadata", {})
