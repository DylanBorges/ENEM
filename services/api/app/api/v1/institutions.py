from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.auth_institution import User, UserRole, Institution, Cohort, CohortMember
from app.models.attempt import Attempt, ScoreEstimate
from app.schemas.institution import InstitutionDashboardOut, CohortOut
from app.api.deps import get_current_user, check_institution_access

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.get("/{institution_id}/dashboard", response_model=InstitutionDashboardOut)
def get_institution_dashboard(
    institution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Isolamento estrito de tenant
    membership = check_institution_access(institution_id, current_user, db)

    # Estudantes não podem acessar visão agregada da instituição
    if membership.role == UserRole.STUDENT and current_user.role != UserRole.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Estudantes não possuem acesso ao painel de gestão institucional.",
        )

    institution = db.scalar(select(Institution).where(Institution.id == institution_id))
    if not institution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instituição não encontrada")

    cohorts = db.scalars(select(Cohort).where(Cohort.institution_id == institution_id)).all()

    cohort_outs = []
    student_ids: set[str] = set()

    for c in cohorts:
        members = db.scalars(select(CohortMember).where(CohortMember.cohort_id == c.id)).all()
        for m in members:
            student_ids.add(m.user_id)
        cohort_outs.append(
            CohortOut(
                id=c.id,
                name=c.name,
                year=c.year,
                student_count=len(members),
            )
        )

    # Coleta de notas dos estudantes da instituição
    if student_ids:
        attempts = db.scalars(select(Attempt).where(Attempt.user_id.in_(student_ids))).all()
        attempt_ids = [att.id for att in attempts]
    else:
        attempts = []
        attempt_ids = []

    if attempt_ids:
        estimates = db.scalars(select(ScoreEstimate).where(ScoreEstimate.attempt_id.in_(attempt_ids))).all()
    else:
        estimates = []

    scores = [e.estimated_score for e in estimates]
    mean_score = float(sum(scores) / len(scores)) if scores else 0.0
    median_score = float(sorted(scores)[len(scores) // 2]) if scores else 0.0

    # Agrupamento por área com anonimização/privacidade LGPD
    dist_by_area: dict[str, dict[str, float | str]] = {}
    for area in ["LC", "CH", "CN", "MT"]:
        area_scores = [e.estimated_score for e in estimates if e.area == area]
        if len(area_scores) >= 5:  # Proteção de privacidade: oculta agregação se N < 5
            dist_by_area[area] = {
                "mean": round(float(sum(area_scores) / len(area_scores)), 1),
                "min": round(float(min(area_scores)), 1),
                "max": round(float(max(area_scores)), 1),
                "count": float(len(area_scores)),
            }
        else:
            dist_by_area[area] = {"status": "insufficient_sample_size"}

    return InstitutionDashboardOut(
        institution_id=institution.id,
        name=institution.name,
        total_students=len(student_ids),
        total_attempts=len(attempts),
        mean_estimated_score=round(mean_score, 1),
        median_estimated_score=round(median_score, 1),
        distribution_by_area=dist_by_area,
        cohorts=cohort_outs,
    )


@router.get("/{institution_id}/cohorts", response_model=list[CohortOut])
def get_institution_cohorts(
    institution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = check_institution_access(institution_id, current_user, db)
    if membership.role == UserRole.STUDENT and current_user.role != UserRole.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Estudantes não possuem acesso às turmas administrativas.",
        )

    cohorts = db.scalars(select(Cohort).where(Cohort.institution_id == institution_id)).all()
    results = []
    for c in cohorts:
        count = db.scalar(
            select(func.count(CohortMember.id)).where(CohortMember.cohort_id == c.id)
        ) or 0
        results.append(
            CohortOut(
                id=c.id,
                name=c.name,
                year=c.year,
                student_count=count,
            )
        )
    return results
