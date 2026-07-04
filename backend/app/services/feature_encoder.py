"""Encode API flow records into model feature vectors."""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np

from ..core.config import FEATURE_COLS_PATH, RF_BUNDLE_PATH
from ..schemas.predict import FlowRecord

logger = logging.getLogger(__name__)


class FeatureEncoder:
    def __init__(self) -> None:
        self.feature_cols: list[str] = []
        self.scaler = None
        self._load()

    def _load(self) -> None:
        if FEATURE_COLS_PATH.exists():
            self.feature_cols = joblib.load(FEATURE_COLS_PATH)
            logger.info("Loaded %d feature columns", len(self.feature_cols))
        elif RF_BUNDLE_PATH.exists():
            bundle = joblib.load(RF_BUNDLE_PATH)
            self.feature_cols = bundle["feature_cols"]
            self.scaler = bundle["scaler"]
            logger.info("Loaded feature cols from RF bundle")
        else:
            logger.warning("No feature columns file — using minimal feature set")

    def _flow_to_dict(self, flow: FlowRecord) -> dict[str, float]:
        return {
            "Source Port": flow.source_port,
            "Destination Port": flow.destination_port,
            "Protocol": flow.protocol,
            "Flow Duration": flow.flow_duration,
            "Total Fwd Packets": flow.total_fwd_packets,
            "Total Backward Packets": flow.total_backward_packets,
            "Flow Bytes/s": flow.flow_bytes_s,
            "Flow Packets/s": flow.flow_packets_s,
            "SYN Flag Count": flow.syn_flag_count,
            "ACK Flag Count": flow.ack_flag_count,
            "packet_ratio_fwd_bwd": flow.total_fwd_packets / (flow.total_backward_packets + 1),
            "duration_packet_rate": flow.flow_duration * flow.flow_packets_s,
            "syn_ack_ratio": flow.syn_flag_count / (flow.ack_flag_count + 1),
        }

    def encode(self, flow: FlowRecord) -> np.ndarray:
        raw = self._flow_to_dict(flow)
        if self.feature_cols:
            vec = np.array([float(raw.get(c, 0.0)) for c in self.feature_cols], dtype=np.float32)
        else:
            vec = np.array(list(raw.values()), dtype=np.float32)
        if self.scaler is not None:
            vec = self.scaler.transform(vec.reshape(1, -1)).astype(np.float32).ravel()
        return vec

    def encode_batch(self, flows: list[FlowRecord]) -> np.ndarray:
        return np.stack([self.encode(f) for f in flows], axis=0)
