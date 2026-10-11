from __future__ import annotations

from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin


class EssayRubric(Base, TimestampedUUIDMixin):
    """Rubrica oficial versionada para avaliação de redação."""
    __tablename__ = "essay_rubrics"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    max_total: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    discrepancy_threshold_total: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    discrepancy_threshold_comp: Mapped[int] = mapped_column(Integer, default=80, nullable=False)

    competencies: Mapped[list["EssayCompetency"]] = relationship(back_populates="rubric", cascade="all, delete-orphan")


class EssayCompetency(Base, TimestampedUUIDMixin):
    """Competência específica dentro de uma rubrica (C1 a C5)."""
    __tablename__ = "essay_competencies"

    rubric_id: Mapped[str] = mapped_column(ForeignKey("essay_rubrics.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)  # C1, C2, C3, C4, C5
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, default=200, nullable=False)

    rubric: Mapped["EssayRubric"] = relationship(back_populates="competencies")


class EssaySubmission(Base, TimestampedUUIDMixin):
    """Submissão de redação de um estudante."""
    __tablename__ = "essay_submissions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rubric_id: Mapped[str] = mapped_column(ForeignKey("essay_rubrics.id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="typed", nullable=False)  # typed, ocr
    status: Mapped[str] = mapped_column(String(30), default="SUBMITTED", nullable=False)  # SUBMITTED, PREGRADED, REVIEWED

    grades: Mapped[list["EssayGrade"]] = relationship(back_populates="submission", cascade="all, delete-orphan")


class EssayGrade(Base, TimestampedUUIDMixin):
    """Avaliação gerada por IA ou corretor humano."""
    __tablename__ = "essay_grades"

    submission_id: Mapped[str] = mapped_column(ForeignKey("essay_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    grader_type: Mapped[str] = mapped_column(String(30), nullable=False)  # AI_PREGRADE, HUMAN_1, HUMAN_2, ADJUDICATOR
    grader_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # ID do corretor ou None se IA
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    submission: Mapped["EssaySubmission"] = relationship(back_populates="grades")
    competency_grades: Mapped[list["CompetencyGrade"]] = relationship(back_populates="grade", cascade="all, delete-orphan")


class CompetencyGrade(Base, TimestampedUUIDMixin):
    """Nota discriminada por competência."""
    __tablename__ = "competency_grades"

    grade_id: Mapped[str] = mapped_column(ForeignKey("essay_grades.id", ondelete="CASCADE"), nullable=False, index=True)
    competency_code: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0, 40, 80, 120, 160, 200
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    probabilities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_spans: Mapped[list | None] = mapped_column(JSON, nullable=True)

    grade: Mapped["EssayGrade"] = relationship(back_populates="competency_grades")
