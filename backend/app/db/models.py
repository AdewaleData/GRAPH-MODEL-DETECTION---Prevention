"""SQLAlchemy ORM models."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


class AlertSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.viewer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    victim_ip: Mapped[str] = mapped_column(String(64), index=True)
    model_name: Mapped[str] = mapped_column(String(32))
    is_attack: Mapped[bool] = mapped_column(Boolean)
    probability: Mapped[float] = mapped_column(Float)
    num_nodes: Mapped[int] = mapped_column(Integer, default=0)
    num_edges: Mapped[int] = mapped_column(Integer, default=0)
    num_flows: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    victim_ip: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    probability: Mapped[float] = mapped_column(Float)
    prediction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(64), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MitigationActionType(str, enum.Enum):
    block = "block"
    rate_limit = "rate_limit"
    quarantine = "quarantine"


class MitigationStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class MitigationRecord(Base):
    __tablename__ = "mitigation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_ip: Mapped[str] = mapped_column(String(64), index=True)
    victim_ip: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[MitigationActionType] = mapped_column(Enum(MitigationActionType))
    status: Mapped[MitigationStatus] = mapped_column(Enum(MitigationStatus), default=MitigationStatus.active)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text)
    rule_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prediction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_triggered: Mapped[bool] = mapped_column(Boolean, default=True)
    detection_to_action_ms: Mapped[float] = mapped_column(Float, default=0.0)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
