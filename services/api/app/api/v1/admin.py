import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.auth_institution import User, UserRole
from app.models.calibration import CalibrationRun
from app.schemas.admin import InepImportRequest, CalibrationRequest, CalibrationOut
from app.api.deps import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/inep/imports")
def trigger_inep_import(
    payload: InepImportRequest,
    admin: User = Depends(require_role(UserRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    raise HTTPException(status_code=501, detail="Importação administrativa ainda não conectada a uma fila persistente")


@router.post("/calibrations", response_model=CalibrationOut, status_code=status.HTTP_201_CREATED)
def create_calibration_run(
    payload: CalibrationRequest,
    admin: User = Depends(require_role(UserRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    raise HTTPException(status_code=422, detail="Publicação exige parâmetros calibrados, vínculo de escala e validação independente; este endpoint não os recebe")


@router.get("/calibrations/{cal_id}", response_model=CalibrationOut)
def get_calibration(
    cal_id: str,
    admin: User = Depends(require_role(UserRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    cal_run = db.scalar(
        select(CalibrationRun).where(
            (CalibrationRun.id == cal_id) | (CalibrationRun.calibration_id == cal_id)
        )
    )
    if not cal_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calibração não encontrada")
    return cal_run
