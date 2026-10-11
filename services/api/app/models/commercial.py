from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin


class Subscription(Base, TimestampedUUIDMixin):
    """Assinatura recorrente B2C ou B2B."""
    __tablename__ = "subscriptions"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False)  # FREE, PREMIUM, SCHOOL_B2B
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Entitlement(Base, TimestampedUUIDMixin):
    """Controle granular de direitos de uso e créditos."""
    __tablename__ = "entitlements"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    feature_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Report(Base, TimestampedUUIDMixin):
    """Relatório PDF gerado para o estudante ou instituição."""
    __tablename__ = "reports"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # STUDENT_INDIVIDUAL, COHORT_SUMMARY
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)  # PENDING, COMPLETED, FAILED
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
