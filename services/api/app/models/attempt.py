from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin


class Attempt(Base, TimestampedUUIDMixin):
    """Tentativa/simulado realizado por um estudante."""
    __tablename__ = "attempts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    booklet_id: Mapped[str] = mapped_column(ForeignKey("booklets.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="IN_PROGRESS", nullable=False)  # IN_PROGRESS, SCORED

    user: Mapped["User"] = relationship(back_populates="attempts")
    booklet: Mapped["Booklet"] = relationship()
    responses: Mapped[list["Response"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")
    score_estimates: Mapped[list["ScoreEstimate"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")


class Response(Base, TimestampedUUIDMixin):
    """Resposta dada a uma posição específica do caderno."""
    __tablename__ = "responses"

    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    physical_position: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_answer: Mapped[str | None] = mapped_column(String(5), nullable=True)  # A, B, C, D, E ou None (em branco)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)  # manual, omr
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # Para OMR

    attempt: Mapped["Attempt"] = relationship(back_populates="responses")
    item: Mapped["Item"] = relationship()


class ScoreEstimate(Base, TimestampedUUIDMixin):
    """Resultado persistido da estimativa de proficiência TRI para uma área."""
    __tablename__ = "score_estimates"

    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(10), nullable=False)
    raw_correct: Mapped[int] = mapped_column(Integer, nullable=False)
    answered_items: Mapped[int] = mapped_column(Integer, nullable=False)
    parameterized_items: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage: Mapped[float] = mapped_column(Float, nullable=False)

    theta_eap: Mapped[float] = mapped_column(Float, nullable=False)
    posterior_sd: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_score: Mapped[float] = mapped_column(Float, nullable=False)
    lower_interval: Mapped[float] = mapped_column(Float, nullable=False)
    upper_interval: Mapped[float] = mapped_column(Float, nullable=False)

    calibration_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # SEMPRE False
    warnings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    attempt: Mapped["Attempt"] = relationship(back_populates="score_estimates")


class Upload(Base, TimestampedUUIDMixin):
    """Arquivo enviado temporariamente pelo usuário (ex: foto de cartão-resposta com TTL)."""
    __tablename__ = "uploads"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    omr_payload: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
