from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.auth_institution import User
from app.models.attempt import Attempt, ScoreEstimate
from app.models.essay import EssaySubmission, EssayGrade
from app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/me")
def get_student_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Tentativas do estudante
    attempts = db.scalars(
        select(Attempt).where(Attempt.user_id == current_user.id).order_by(Attempt.created_at.desc())
    ).all()

    evolution_records = []
    for att in attempts:
        estimates = db.scalars(
            select(ScoreEstimate).where(ScoreEstimate.attempt_id == att.id)
        ).all()
        if estimates:
            evolution_records.append(
                {
                    "attempt_id": att.id,
                    "date": att.created_at.isoformat(),
                    "status": att.status,
                    "areas": [
                        {
                            "area": e.area,
                            "estimated_score": e.estimated_score,
                            "posterior_sd": e.posterior_sd,
                            "raw_correct": e.raw_correct,
                            "coverage": e.coverage,
                            "calibration_id": e.calibration_id,
                            "is_official": e.official,
                        }
                        for e in estimates
                    ],
                }
            )
        else:
            from app.models.attempt import Response
            responses = db.scalars(select(Response).where(Response.attempt_id == att.id)).all()
            if responses:
                correct_count = sum(1 for r in responses if r.is_correct is True)
                evolution_records.append(
                    {
                        "attempt_id": att.id,
                        "date": att.created_at.isoformat(),
                        "status": att.status,
                        "areas": [
                            {
                                "area": "GERAL",
                                "estimated_score": 0.0,
                                "posterior_sd": 0.0,
                                "raw_correct": correct_count,
                                "coverage": 1.0,
                                "calibration_id": "GABARITO_OFICIAL",
                                "is_official": False,
                            }
                        ],
                    }
                )

    # Redações do estudante
    essays = db.scalars(
        select(EssaySubmission).where(EssaySubmission.user_id == current_user.id).order_by(EssaySubmission.created_at.desc())
    ).all()

    essay_records = []
    for ess in essays:
        last_grade = db.scalar(
            select(EssayGrade).where(EssayGrade.submission_id == ess.id).order_by(EssayGrade.created_at.desc())
        )
        essay_records.append(
            {
                "submission_id": ess.id,
                "topic": ess.topic,
                "status": ess.status,
                "total_score": last_grade.total_score if last_grade else None,
                "grader_type": last_grade.grader_type if last_grade else None,
                "created_at": ess.created_at.isoformat(),
            }
        )

    return {
        "student": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "target_year": current_user.target_year,
            "target_course": current_user.target_course,
        },
        "total_attempts": len(attempts),
        "total_essays": len(essays),
        "evolution": evolution_records,
        "recent_essays": essay_records,
        "disclaimer": "Todas as notas exibidas são estimativas independentes e não constituem nota oficial do INEP.",
    }
