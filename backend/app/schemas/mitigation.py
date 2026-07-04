"""Mitigation schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class MitigationRecordResponse(BaseModel):
    id: int
    source_ip: str
    victim_ip: str
    action: str
    status: str
    score: float
    reason: str
    rule_text: str | None
    alert_id: int | None
    prediction_id: int | None
    auto_triggered: bool
    detection_to_action_ms: float
    applied_at: datetime
    revoked_at: datetime | None

    class Config:
        from_attributes = True


class MitigationApplyRequest(BaseModel):
    source_ip: str
    victim_ip: str
    action: str = "block"
    reason: str = "Manual prevention action"


class MitigationRevokeRequest(BaseModel):
    record_id: int | None = None
    source_ip: str | None = None


class MitigationSummary(BaseModel):
    active_blocks: int
    active_rate_limits: int
    active_quarantines: int
    total_active: int
    total_applied: int
    total_revoked: int
    avg_time_to_mitigate_ms: float
    mode: str
    auto_enabled: bool


class BlocklistEntry(BaseModel):
    source_ip: str
    victim_ip: str
    action: str
    record_id: int
    applied_at: str | None


class BlocklistResponse(BaseModel):
    blocked: list[BlocklistEntry]
    rate_limited: list[BlocklistEntry]
    quarantined: list[BlocklistEntry]
    stats: dict


class PreventionStatsResponse(BaseModel):
    flows_blocked: int = 0
    flows_allowed: int = 0
    mitigation_summary: MitigationSummary
