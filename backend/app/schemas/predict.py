"""Prediction schemas."""

from pydantic import BaseModel, Field


class FlowRecord(BaseModel):
    source_ip: str = Field(..., max_length=64)
    destination_ip: str = Field(..., max_length=64)
    source_port: float = 0
    destination_port: float = 0
    protocol: float = 6
    flow_duration: float = 0
    total_fwd_packets: float = 0
    total_backward_packets: float = 0
    flow_bytes_s: float = 0
    flow_packets_s: float = 1.0
    syn_flag_count: float = 0
    ack_flag_count: float = 1
    # Additional features filled with 0 if missing during encoding


class PredictRequest(BaseModel):
    flows: list[FlowRecord] = Field(min_length=1, max_length=128)
    victim_ip: str | None = None
    model: str = Field(default="gcn", pattern="^(gcn|gat|rf)$")


class PredictResponse(BaseModel):
    is_attack: bool
    probability: float
    model: str
    victim_ip: str
    num_nodes: int
    num_edges: int
    num_flows: int
    latency_ms: float
    message: str
