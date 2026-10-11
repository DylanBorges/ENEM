from __future__ import annotations

from sqlalchemy import String, Integer, Float, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin


class CalibrationRun(Base, TimestampedUUIDMixin):
    """Registro auditável e imutável de uma rodada de calibração psicométrica."""
    __tablename__ = "calibration_runs"

    calibration_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    exam_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    application: Mapped[str] = mapped_column(String(50), default="regular", nullable=False)
    area: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # LC, CH, CN, MT
    irt_model: Mapped[str] = mapped_column(String(20), default="3PL", nullable=False)
    estimator: Mapped[str] = mapped_column(String(20), default="EAP", nullable=False)
    D: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    scale_alpha: Mapped[float] = mapped_column(Float, nullable=False)
    scale_beta: Mapped[float] = mapped_column(Float, nullable=False)
    minimum_coverage: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)

    dataset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    code_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PUBLISHED", nullable=False)  # DRAFT, PUBLISHED, DEPRECATED
    official_algorithm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    parameters: Mapped[list["ItemParameterModel"]] = relationship(
        back_populates="calibration_run", cascade="all, delete-orphan"
    )


class ItemParameterModel(Base, TimestampedUUIDMixin):
    """Parâmetros calibrados (a, b, c) de um item específico em uma dada rodada de calibração."""
    __tablename__ = "item_parameters"

    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    calibration_run_id: Mapped[str] = mapped_column(
        ForeignKey("calibration_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    a: Mapped[float] = mapped_column(Float, nullable=False)
    b: Mapped[float] = mapped_column(Float, nullable=False)
    c: Mapped[float] = mapped_column(Float, nullable=False)
    D: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)

    item: Mapped["Item"] = relationship(back_populates="parameters")
    calibration_run: Mapped["CalibrationRun"] = relationship(back_populates="parameters")
