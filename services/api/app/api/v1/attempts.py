import os
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select, exists

from app.core.config import settings
from app.db.session import get_db
from app.models.auth_institution import User
from app.models.exam import Booklet, BookletItem, Exam, Item
from app.models.attempt import Attempt, Response, Upload, ScoreEstimate
from app.models.calibration import CalibrationRun
from app.schemas.attempt import AttemptCreate, AttemptOut, AttemptResponsesUpdate, ResponseOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
def create_attempt(
    payload: AttemptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booklet = db.scalar(
        select(Booklet).join(Exam, Booklet.exam_id == Exam.id).where(
            Booklet.id == payload.booklet_id, Exam.is_active == True
        )
    )
    if not booklet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caderno não encontrado")

    attempt = Attempt(
        user_id=current_user.id,
        booklet_id=payload.booklet_id,
        status="IN_PROGRESS",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/{attempt_id}", response_model=AttemptOut)
def get_attempt(
    attempt_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(
        select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulado não encontrado")
    return attempt


@router.put("/{attempt_id}/responses", response_model=list[ResponseOut])
def update_responses(
    attempt_id: str,
    payload: AttemptResponsesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(
        select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulado não encontrado")

    # Mapeamento do caderno: physical_position -> BookletItem
    booklet_items = db.scalars(
        select(BookletItem).where(BookletItem.booklet_id == attempt.booklet_id)
    ).all()
    position_map = {bi.physical_position: bi for bi in booklet_items}

    # Respostas existentes
    existing_responses = db.scalars(
        select(Response).where(Response.attempt_id == attempt_id)
    ).all()
    resp_map = {r.physical_position: r for r in existing_responses}

    updated_list = []
    for item_input in payload.responses:
        bi = position_map.get(item_input.position)
        if not bi:
            raise HTTPException(status_code=422, detail=f"Posição {item_input.position} não pertence ao caderno")

        selected = item_input.answer.upper() if item_input.answer else None
        is_corr = item_input.is_correct
        # Item anulado não equivale a resposta correta para estimativa psicométrica.
        if bi.answer_key == "*":
            is_corr = None
        elif is_corr is None and selected is not None:
            is_corr = selected == bi.answer_key.upper()
        elif is_corr is True and selected is None:
            selected = bi.answer_key.upper()

        if item_input.position in resp_map:
            resp_obj = resp_map[item_input.position]
            resp_obj.selected_answer = selected
            resp_obj.is_correct = is_corr
            resp_obj.source = item_input.source
        else:
            resp_obj = Response(
                attempt_id=attempt.id,
                item_id=bi.item_id,
                physical_position=item_input.position,
                selected_answer=selected,
                is_correct=is_corr,
                source=item_input.source,
            )
            db.add(resp_obj)
        updated_list.append(resp_obj)

    db.commit()
    for r in updated_list:
        db.refresh(r)
    return updated_list


@router.post("/{attempt_id}/answer-sheet")
async def upload_answer_sheet(
    attempt_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(
        select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulado não encontrado")

    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato inválido. Envie imagem JPEG ou PNG.",
        )

    os.makedirs(settings.OMR_IMAGE_UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.OMR_IMAGE_UPLOAD_DIR, filename)

    contents = await file.read()
    if len(contents) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo excede limite de 15MB",
        )

    with open(file_path, "wb") as f:
        f.write(contents)

    # Registro de Upload temporário com TTL de 24h conforme LGPD privacy by design
    upload_record = Upload(
        user_id=current_user.id,
        attempt_id=attempt_id,
        filename=filename,
        file_path=file_path,
        mime_type=file.content_type,
        status="CONFIRMATION_REQUIRED",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(upload_record)
    db.commit()
    db.refresh(upload_record)

    return {
        "job_id": upload_record.id,
        "status": "requires_confirmation",
        "message": "Cartão-resposta pré-processado. Confirme as alternativas antes do scoring definitivo.",
    }


@router.get("/{attempt_id}/summary")
def get_attempt_summary(
    attempt_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(
        select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulado não encontrado")

    booklet = db.scalar(select(Booklet).where(Booklet.id == attempt.booklet_id))
    exam = db.scalar(select(Exam).where(Exam.id == booklet.exam_id))

    responses = db.scalars(select(Response).where(Response.attempt_id == attempt_id)).all()
    resp_map = {r.physical_position: r for r in responses}

    b_items_query = (
        select(BookletItem, Item)
        .join(Item, BookletItem.item_id == Item.id)
        .where(BookletItem.booklet_id == booklet.id)
        .order_by(BookletItem.physical_position)
    )
    b_items = db.execute(b_items_query).all()

    estimates = db.scalars(select(ScoreEstimate).where(ScoreEstimate.attempt_id == attempt_id)).all()
    est_by_area = {e.area: e for e in estimates}

    empty_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    has_tri = bool(db.scalar(
        select(exists().where(
            CalibrationRun.exam_year == exam.year,
            CalibrationRun.application == exam.application,
            CalibrationRun.status == "PUBLISHED",
            CalibrationRun.dataset_sha256 != empty_sha256,
        ))
    ))

    items_result = []
    area_stats = {}
    total_correct = 0

    for bi, itm in b_items:
        r = resp_map.get(bi.physical_position)
        selected = r.selected_answer if r else None
        is_corr = r.is_correct if r else None
        annulled = bi.answer_key == "*"

        if annulled:
            is_corr = None
        elif is_corr is None and selected is not None:
            is_corr = selected.upper() == bi.answer_key.upper()

        if is_corr is True:
            total_correct += 1

        stats = area_stats.setdefault(itm.area, {"raw_correct": 0, "total": 0, "annulled": 0})
        stats["total"] += 1
        if annulled:
            stats["annulled"] += 1
        elif is_corr is True:
            stats["raw_correct"] += 1

        items_result.append({
            "position": bi.physical_position,
            "area": itm.area,
            "selected_answer": selected,
            "official_key": bi.answer_key,
            "is_correct": is_corr,
            "annulled": annulled,
        })

    areas_out = []
    for area, stats in area_stats.items():
        est = est_by_area.get(area)
        valid = stats["total"] - stats["annulled"]
        pct = (stats["raw_correct"] / valid * 100) if valid > 0 else 0.0
        areas_out.append({
            "area": area,
            "raw_correct": stats["raw_correct"],
            "total_items": stats["total"],
            "percentage": round(pct, 1),
            "estimated_score": round(est.estimated_score, 1) if est else None,
            "theta_eap": round(est.theta_eap, 3) if est else None,
            "interval_95": (round(est.lower_interval, 1), round(est.upper_interval, 1)) if est else None,
        })

    if not has_tri and attempt.status != "SCORED":
        attempt.status = "SCORED"
        db.commit()

    return {
        "attempt_id": attempt.id,
        "exam_id": exam.id,
        "exam_title": exam.title,
        "year": exam.year,
        "day": booklet.day,
        "booklet_color": booklet.color,
        "booklet_description": booklet.description,
        "status": attempt.status,
        "has_tri_calibration": has_tri,
        "total_correct": total_correct,
        "total_items": len(b_items),
        "areas": areas_out,
        "items": items_result,
        "disclaimer": (
            "Correção oficial baseada no gabarito do Inep. "
            + ("Nota TRI calculada com calibração oficial." if has_tri else "Calibração psicométrica TRI ativa para as edições 2024 e 2025.")
        ),
    }

