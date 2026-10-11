from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.auth_institution import User
from app.models.commercial import Report
from app.models.attempt import Attempt
from app.schemas.report import ReportCreate, ReportOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def request_report(
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.attempt_id:
        attempt = db.scalar(
            select(Attempt).where(Attempt.id == payload.attempt_id, Attempt.user_id == current_user.id)
        )
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulado não encontrado")

    report = Report(
        user_id=current_user.id,
        attempt_id=payload.attempt_id,
        report_type=payload.report_type,
        status="COMPLETED",
        file_path=f"/reports/{current_user.id}/report_{payload.attempt_id or 'general'}.pdf",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    out = ReportOut.from_orm(report)
    out.download_url = f"/v1/reports/{report.id}/download"
    return out


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.scalar(
        select(Report).where(Report.id == report_id, Report.user_id == current_user.id)
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relatório não encontrado")

    out = ReportOut.from_orm(report)
    out.download_url = f"/v1/reports/{report.id}/download"
    return out
