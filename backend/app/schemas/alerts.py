"""Alert schemas."""

from datetime import datetime

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: int
    victim_ip: str
    severity: str
    title: str
    message: str
    probability: float
    acknowledged: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertAckRequest(BaseModel):
    alert_id: int
