"""GNN / RF model inference engine — singleton loaded at startup."""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import torch
from torch_geometric.data import Data

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from ddos_gnn.models import GATGraphClassifier, GCNGraphClassifier  # noqa: E402

from ..core.config import GAT_MODEL_PATH, GCN_MODEL_PATH, INFERENCE_DEVICE, RF_BUNDLE_PATH
from ..schemas.predict import FlowRecord
from .feature_encoder import FeatureEncoder

logger = logging.getLogger(__name__)


def _load_state_dict(path: Path) -> dict:
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    return ckpt.get("state_dict", ckpt)


def _build_gcn_from_state(state: dict) -> GCNGraphClassifier:
    hidden = int(state["convs.0.bias"].shape[0])
    in_ch = int(state["convs.0.lin.weight"].shape[1])
    n_convs = len({k.split(".")[1] for k in state if k.startswith("convs.") and k.endswith(".bias")})
    model = GCNGraphClassifier(
        in_channels=in_ch,
        hidden_channels=hidden,
        out_channels=2,
        num_layers=n_convs,
    )
    model.load_state_dict(state)
    return model


def _build_gat_from_state(state: dict) -> GATGraphClassifier:
    in_ch = int(state["gat1.lin.weight"].shape[1])
    hidden = int(state["gat1.lin.weight"].shape[0]) // 4  # concat heads
    model = GATGraphClassifier(in_channels=in_ch, hidden_channels=hidden, heads=4, out_channels=2)
    model.load_state_dict(state)
    return model


class InferenceEngine:
    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() and INFERENCE_DEVICE != "cpu" else "cpu")
        self.encoder = FeatureEncoder()
        self.gcn: GCNGraphClassifier | None = None
        self.gat: GATGraphClassifier | None = None
        self.rf_bundle: dict | None = None
        self.gcn_meta: dict = {}
        self.gat_meta: dict = {}
        self.gcn_threshold = 0.5
        self.gat_threshold = 0.5
        self._loaded = False

    def load_models(self) -> None:
        if self._loaded:
            return
        logger.info("Loading models on device=%s", self.device)

        if GCN_MODEL_PATH.exists():
            meta_path = GCN_MODEL_PATH.with_suffix(".json")
            self.gcn_meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            state = _load_state_dict(GCN_MODEL_PATH)
            self.gcn = _build_gcn_from_state(state)
            self.gcn.to(self.device).eval()
            self.gcn_threshold = float(self.gcn_meta.get("threshold", 0.5))
            logger.info("GCN loaded hidden=%d layers=%d threshold=%.3f",
                        int(state["convs.0.bias"].shape[0]),
                        len({k.split('.')[1] for k in state if k.startswith('convs.')}),
                        self.gcn_threshold)

        if GAT_MODEL_PATH.exists():
            meta_path = GAT_MODEL_PATH.with_suffix(".json")
            self.gat_meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            try:
                state = _load_state_dict(GAT_MODEL_PATH)
                self.gat = _build_gat_from_state(state)
                self.gat.to(self.device).eval()
                self.gat_threshold = float(self.gat_meta.get("threshold", 0.5))
                logger.info("GAT loaded threshold=%.3f", self.gat_threshold)
            except Exception as exc:
                logger.warning("GAT load skipped: %s", exc)

        if RF_BUNDLE_PATH.exists():
            self.rf_bundle = joblib.load(RF_BUNDLE_PATH)
            logger.info("RF bundle loaded")

        self._loaded = True

    @torch.no_grad()
    def predict_graph(self, data: Data, model_name: str = "gcn") -> tuple[bool, float, float]:
        start = time.perf_counter()
        data = data.to(self.device)
        batch = torch.zeros(data.num_nodes, dtype=torch.long, device=self.device)

        if model_name == "gat" and self.gat is not None:
            logits = self.gat(data.x, data.edge_index, batch, data.edge_attr)
            threshold = self.gat_threshold
        elif self.gcn is not None:
            logits = self.gcn(data.x, data.edge_index, batch, data.edge_attr)
            threshold = self.gcn_threshold
        else:
            raise RuntimeError("No GNN model loaded")

        prob = torch.softmax(logits, dim=-1)[0, 1].item()
        is_attack = prob >= threshold
        latency_ms = (time.perf_counter() - start) * 1000
        return is_attack, prob, latency_ms

    def predict_flows_rf(self, flows: list[FlowRecord]) -> tuple[bool, float, float]:
        if not self.rf_bundle:
            raise RuntimeError("RF model not loaded")
        from ddos_gnn.inference import predict_flow_sklearn

        start = time.perf_counter()
        probs = []
        for flow in flows:
            vec = self.encoder.encode(flow)
            _, p = predict_flow_sklearn(self.rf_bundle, vec)
            probs.append(p)
        mean_prob = float(np.mean(probs))
        is_attack = mean_prob >= 0.5
        latency_ms = (time.perf_counter() - start) * 1000
        return is_attack, mean_prob, latency_ms


inference_engine = InferenceEngine()
