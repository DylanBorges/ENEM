from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.auth_institution import User
from app.models.exam import Booklet, BookletItem, Item, Exam
from app.models.attempt import Attempt, Response, ScoreEstimate
from app.models.calibration import CalibrationRun, ItemParameterModel
from app.schemas.scoring import AttemptScoreResponse, AreaScoreResponse
from app.api.deps import get_current_user

from tri_core.models import ItemParameter, CalibrationVersion
from tri_core.eap import score_pattern

router = APIRouter(prefix="/attempts", tags=["scoring"])


@router.post("/{attempt_id}/score", response_model=AttemptScoreResponse)
def calculate_attempt_score(
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
    if not booklet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caderno não encontrado")

    exam = db.scalar(select(Exam).where(Exam.id == booklet.exam_id))
    if not exam or not exam.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exame não encontrado")

    # Respostas do estudante
    responses = db.scalars(select(Response).where(Response.attempt_id == attempt_id)).all()
    resp_by_item = {r.item_id: r for r in responses}

    # Itens do caderno organizados por área
    booklet_items_query = (
        select(BookletItem, Item)
        .join(Item, BookletItem.item_id == Item.id)
        .where(BookletItem.booklet_id == booklet.id)
        .order_by(BookletItem.physical_position)
    )
    items_by_area: dict[str, list[tuple[BookletItem, Item]]] = {}
    for bi, itm in db.execute(booklet_items_query).all():
        items_by_area.setdefault(itm.area, []).append((bi, itm))

    if not items_by_area:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum item associado ao caderno de prova",
        )

    scored_areas: list[AreaScoreResponse] = []

    # Processa cada área presente na prova
    for area, area_items in items_by_area.items():
        # Busca calibração publicada e válida
        cal_run = db.scalar(
            select(CalibrationRun).where(
                CalibrationRun.exam_year == exam.year,
                CalibrationRun.application == exam.application,
                CalibrationRun.area == area,
                CalibrationRun.status == "PUBLISHED",
            )
        )
        if not cal_run:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Calibração psicométrica ausente ou não publicada para a área '{area}' "
                    f"do exame {exam.year} ({exam.application}). Parâmetros oficiais não são fabricados."
                ),
            )

        if cal_run.dataset_sha256 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
            raise HTTPException(status_code=422, detail="Calibração inválida: hash do conjunto de dados vazio")

        # Carrega parâmetros da calibração
        param_rows = db.scalars(
            select(ItemParameterModel).where(ItemParameterModel.calibration_run_id == cal_run.id)
        ).all()
        param_dict = {
            p.item_id: ItemParameter(a=p.a, b=p.b, c=p.c, D=p.D, item_id=p.item_id)
            for p in param_rows
        }

        # Constrói vetores de respostas e parâmetros
        area_responses: list[int | None] = []
        area_params: list[ItemParameter | None] = []

        for bi, itm in area_items:
            if bi.answer_key == "*":
                area_responses.append(None)
                area_params.append(None)
                continue
            r = resp_by_item.get(itm.id)
            if r and r.is_correct is not None:
                area_responses.append(1 if r.is_correct else 0)
            elif r and r.selected_answer is not None:
                # Caso selected_answer exista mas is_correct não tenha sido gravado
                is_c = r.selected_answer.upper() == bi.answer_key.upper()
                area_responses.append(1 if is_c else 0)
            else:
                area_responses.append(None)  # Em branco

            area_params.append(param_dict.get(itm.id))

        # Objeto de calibração do tri_core
        tri_cal = CalibrationVersion(
            calibration_id=cal_run.calibration_id,
            exam_year=cal_run.exam_year,
            application=cal_run.application,
            area=cal_run.area,
            irt_model=cal_run.irt_model,
            estimator=cal_run.estimator,
            D=cal_run.D,
            scale_alpha=cal_run.scale_alpha,
            scale_beta=cal_run.scale_beta,
            minimum_coverage=cal_run.minimum_coverage,
            dataset_sha256=cal_run.dataset_sha256,
            code_version=cal_run.code_version,
            status=cal_run.status,
            official_algorithm=False,
        )

        try:
            score_out = score_pattern(
                responses=area_responses,
                items=area_params,
                calibration=tri_cal,
                expected_total_items=len(area_items),
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Remove estimativas anteriores para esta área nesta tentativa
        old_est = db.scalar(
            select(ScoreEstimate).where(
                ScoreEstimate.attempt_id == attempt.id,
                ScoreEstimate.area == area,
            )
        )
        if old_est:
            db.delete(old_est)

        estimate_rec = ScoreEstimate(
            attempt_id=attempt.id,
            area=area,
            raw_correct=score_out.raw_correct,
            answered_items=score_out.answered_items,
            parameterized_items=score_out.parameterized_items,
            coverage=score_out.coverage,
            theta_eap=score_out.theta_eap,
            posterior_sd=score_out.posterior_sd,
            estimated_score=score_out.score_estimated,
            lower_interval=score_out.credible_interval_95[0],
            upper_interval=score_out.credible_interval_95[1],
            calibration_id=score_out.calibration_id,
            model_version=score_out.model_version,
            official=False,  # Sempre falso
            warnings=score_out.warnings,
        )
        db.add(estimate_rec)

        scored_areas.append(
            AreaScoreResponse(
                area=area,
                raw_correct=score_out.raw_correct,
                answered_items=score_out.answered_items,
                parameterized_items=score_out.parameterized_items,
                coverage=score_out.coverage,
                theta_eap=score_out.theta_eap,
                posterior_sd=score_out.posterior_sd,
                score_estimated=score_out.score_estimated,
                credible_interval_95=score_out.credible_interval_95,
                method="3PL_EAP",
                calibration_id=score_out.calibration_id,
                model_version=score_out.model_version,
                official=False,
            )
        )

    attempt.status = "SCORED"
    db.commit()

    return AttemptScoreResponse(attempt_id=attempt.id, areas=scored_areas)


@router.get("/{attempt_id}/score", response_model=AttemptScoreResponse)
def get_attempt_score(
    attempt_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(
        select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulado não encontrado")

    estimates = db.scalars(select(ScoreEstimate).where(ScoreEstimate.attempt_id == attempt_id)).all()
    if not estimates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota ainda não calculada")

    areas = [
        AreaScoreResponse(
            area=e.area,
            raw_correct=e.raw_correct,
            answered_items=e.answered_items,
            parameterized_items=e.parameterized_items,
            coverage=e.coverage,
            theta_eap=e.theta_eap,
            posterior_sd=e.posterior_sd,
            score_estimated=e.estimated_score,
            credible_interval_95=(e.lower_interval, e.upper_interval),
            method="3PL_EAP",
            calibration_id=e.calibration_id,
            model_version=e.model_version,
            official=False,
        )
        for e in estimates
    ]
    return AttemptScoreResponse(attempt_id=attempt.id, areas=areas)
