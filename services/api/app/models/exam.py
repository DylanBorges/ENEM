from __future__ import annotations

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin


class Exam(Base, TimestampedUUIDMixin):
    """Representa uma edição do exame (ex: ENEM 2025 Aplicação Regular)."""
    __tablename__ = "exams"

    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    application: Mapped[str] = mapped_column(String(50), default="regular", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    booklets: Mapped[list["Booklet"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    items: Mapped[list["Item"]] = relationship(back_populates="exam", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("year", "application", name="uq_exam_year_application"),
    )


class Booklet(Base, TimestampedUUIDMixin):
    """Caderno físico de prova (ex: ENEM 2025 Dia 1 Azul - Inglês)."""
    __tablename__ = "booklets"

    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    day: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 ou 2
    color: Mapped[str] = mapped_column(String(50), nullable=False)  # Azul, Amarelo, Branco, Rosa, etc.
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)  # INGLES, ESPANHOL ou None
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    exam: Mapped["Exam"] = relationship(back_populates="booklets")
    booklet_items: Mapped[list["BookletItem"]] = relationship(back_populates="booklet", cascade="all, delete-orphan")


class Item(Base, TimestampedUUIDMixin):
    """Item psicométrico abstrato. É invariante à cor ou posição física do caderno."""
    __tablename__ = "items"

    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # LC, CH, CN, MT
    official_item_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    skill_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    exam: Mapped["Exam"] = relationship(back_populates="items")
    booklet_items: Mapped[list["BookletItem"]] = relationship(back_populates="item", cascade="all, delete-orphan")
    parameters: Mapped[list["ItemParameterModel"]] = relationship(back_populates="item", cascade="all, delete-orphan")


class BookletItem(Base, TimestampedUUIDMixin):
    """Mapeamento obrigatório da posição física (1..180) para o item estatístico e gabarito oficial."""
    __tablename__ = "booklet_items"

    booklet_id: Mapped[str] = mapped_column(ForeignKey("booklets.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    physical_position: Mapped[int] = mapped_column(Integer, nullable=False)  # Posição na folha (ex: 1 a 90)
    answer_key: Mapped[str] = mapped_column(String(5), nullable=False)  # A, B, C, D, E ou * (anulada)

    booklet: Mapped["Booklet"] = relationship(back_populates="booklet_items")
    item: Mapped["Item"] = relationship(back_populates="booklet_items")

    __table_args__ = (
        UniqueConstraint("booklet_id", "physical_position", name="uq_booklet_physical_position"),
    )
