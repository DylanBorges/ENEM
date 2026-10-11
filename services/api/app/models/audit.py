from __future__ import annotations

from sqlalchemy import String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class AuditLog(Base, TimestampedUUIDMixin):
    """Trilha de auditoria para ações sensíveis, calibrações, notas humanas e compliance LGPD."""
    __tablename__ = "audit_logs"

    actor_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class UsageEvent(Base, TimestampedUUIDMixin):
    """Eventos de telemetria de produto sem dados pessoais identificáveis (LGPD compliance)."""
    __tablename__ = "usage_events"

    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    institution_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
