"""Metrics schemas."""

from datetime import datetime

from pydantic import BaseModel


class MetricsSummary(BaseModel):
    total_predictions: int
    attack_predictions: int
    benign_predictions: int
    total_alerts: int
    unacknowledged_alerts: int
    avg_latency_ms: float
    attack_rate: float
    active_mitigations: int = 0
    flows_blocked: int = 0
    avg_time_to_mitigate_ms: float = 0.0


class PredictionHistoryItem(BaseModel):
    id: int
    victim_ip: str
    model_name: str
    is_attack: bool
    probability: float
    latency_ms: float
    created_at: datetime

    class Config:
        from_attributes = True
