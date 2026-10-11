from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.auth_institution import User
from app.models.essay import EssayRubric, EssayCompetency, EssaySubmission, EssayGrade, CompetencyGrade
from app.schemas.essay import EssayCreate, EssayPregradeResponse, CompetencyPrediction, HumanReviewRequest
from app.api.deps import get_current_user

router = APIRouter(prefix="/essays", tags=["essays"])


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_essay(
    payload: EssayCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rubric = db.scalar(select(EssayRubric).order_by(EssayRubric.year.desc()))
    if not rubric:
        # Cria rubrica padrão caso banco esteja recém-inicializado
        rubric = EssayRubric(name="Matriz ENEM 2026", year=2026)
        db.add(rubric)
        db.commit()
        db.refresh(rubric)

    submission = EssaySubmission(
        user_id=current_user.id,
        rubric_id=rubric.id,
        topic=payload.topic,
        text=payload.text,
        source=payload.source,
        status="SUBMITTED",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {"id": submission.id, "status": submission.status, "topic": submission.topic}


@router.post("/{essay_id}/pregrade", response_model=EssayPregradeResponse)
def pregrade_essay(
    essay_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submission = db.scalar(
        select(EssaySubmission).where(
            EssaySubmission.id == essay_id, EssaySubmission.user_id == current_user.id
        )
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redação não encontrada")

    from app.services.gemini_essay_service import (
        AssessmentUnavailable, InvalidAssessment, evaluate_essay_with_gemini,
    )

    try:
        eval_result = evaluate_essay_with_gemini(topic=submission.topic, text=submission.text)
    except AssessmentUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InvalidAssessment as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    grade = EssayGrade(
        submission_id=submission.id,
        grader_type="AI_PREGRADE",
        total_score=eval_result.total_score,
        is_final=False,
        notes=f"{eval_result.model_used}; prompt={eval_result.prompt_version}",
    )
    db.add(grade)
    db.flush()

    predictions = []
    for comp in eval_result.competencies:
        cg = CompetencyGrade(
            grade_id=grade.id,
            competency_code=comp.code,
            score=comp.predicted_score,
            confidence=comp.confidence,
            probabilities=None,
            feedback=comp.feedback,
            evidence_spans=comp.evidence_spans,
        )
        db.add(cg)
        predictions.append(
            CompetencyPrediction(
                competency=comp.code,
                predicted_score=comp.predicted_score,
                probabilities={},
                confidence=comp.confidence,
                feedback=comp.feedback,
                evidence_spans=comp.evidence_spans,
                requires_human_review=comp.requires_human_review,
            )
        )

    submission.status = "PREGRADED"
    db.commit()

    return EssayPregradeResponse(
        submission_id=submission.id,
        status="PREGRADED",
        total_score=eval_result.total_score,
        competencies=predictions,
        model_version=f"{eval_result.model_used}; {eval_result.prompt_version}",
    )


@router.post("/{essay_id}/human-review")
def request_human_review(
    essay_id: str,
    payload: HumanReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submission = db.scalar(
        select(EssaySubmission).where(
            EssaySubmission.id == essay_id, EssaySubmission.user_id == current_user.id
        )
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redação não encontrada")

    submission.status = "PENDING_HUMAN_REVIEW"
    db.commit()

    return {
        "submission_id": submission.id,
        "status": "PENDING_HUMAN_REVIEW",
        "message": "Solicitação registrada. Não há atribuição automática a revisores nesta versão.",
    }
