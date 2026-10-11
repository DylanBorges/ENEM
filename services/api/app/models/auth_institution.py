from __future__ import annotations

import enum
from sqlalchemy import String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampedUUIDMixin


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    INSTITUTION_ADMIN = "INSTITUTION_ADMIN"
    REVIEWER = "REVIEWER"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"


class User(Base, TimestampedUUIDMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.STUDENT,
        nullable=False,
    )
    target_year: Mapped[int | None] = mapped_column(nullable=True)
    target_course: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relacionamentos
    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    cohort_memberships: Mapped[list["CohortMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Institution(Base, TimestampedUUIDMixin):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    document_cnpj: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="institution", cascade="all, delete-orphan")
    cohorts: Mapped[list["Cohort"]] = relationship(back_populates="institution", cascade="all, delete-orphan")


class Membership(Base, TimestampedUUIDMixin):
    """Vínculo de controle de acesso RBAC entre usuário e instituição."""
    __tablename__ = "memberships"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)

    user: Mapped["User"] = relationship(back_populates="memberships")
    institution: Mapped["Institution"] = relationship(back_populates="memberships")


class Cohort(Base, TimestampedUUIDMixin):
    """Turma de alunos pertencente a uma instituição."""
    __tablename__ = "cohorts"

    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)

    institution: Mapped["Institution"] = relationship(back_populates="cohorts")
    members: Mapped[list["CohortMember"]] = relationship(back_populates="cohort", cascade="all, delete-orphan")


class CohortMember(Base, TimestampedUUIDMixin):
    __tablename__ = "cohort_members"

    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    cohort: Mapped["Cohort"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="cohort_memberships")
