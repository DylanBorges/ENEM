from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, exists

from app.db.session import get_db
from app.models.exam import Exam, Booklet, BookletItem, Item
from app.models.calibration import CalibrationRun
from app.schemas.exam import ExamOut, BookletOut, BookletItemOut

router = APIRouter(prefix="/exams", tags=["exams"])

REGULAR_2025_PAPERS = {
    (1, "AZUL"): 1, (1, "AMARELA"): 2, (1, "BRANCA"): 3, (1, "VERDE"): 4,
    (2, "AMARELA"): 5, (2, "CINZA"): 6, (2, "AZUL"): 7, (2, "VERDE"): 8,
}
REGULAR_2024_PAPERS = {(1, "AZUL"): 1, (2, "AZUL"): 7}
PAST_PAPERS = {
    (1, "AZUL"): 1,
    (2, "AMARELO"): 5,
    (2, "AMARELA"): 5,
}

BOOKLETS_DIR = Path(__file__).resolve().parents[4] / "data/booklets"


@router.get("", response_model=list[ExamOut])
def list_exams(all: bool = False, db: Session = Depends(get_db)):
    empty_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    verified_calibration = exists().where(
        CalibrationRun.exam_year == Exam.year,
        CalibrationRun.application == Exam.application,
        CalibrationRun.status == "PUBLISHED",
        CalibrationRun.dataset_sha256 != empty_sha256,
    )
    if all:
        exams = db.scalars(select(Exam).where(Exam.is_active == True).order_by(Exam.year.desc())).all()
    else:
        exams = db.scalars(select(Exam).where(Exam.is_active == True, verified_calibration).order_by(Exam.year.desc())).all()

    results = []
    for exam in exams:
        has_cal = db.scalar(
            select(exists().where(
                CalibrationRun.exam_year == exam.year,
                CalibrationRun.application == exam.application,
                CalibrationRun.status == "PUBLISHED",
                CalibrationRun.dataset_sha256 != empty_sha256,
            ))
        )
        results.append(
            ExamOut(
                id=exam.id,
                year=exam.year,
                application=exam.application,
                title=exam.title,
                has_calibration=bool(has_cal),
            )
        )
    return results


@router.get("/{exam_id}/booklets", response_model=list[BookletOut])
def get_exam_booklets(exam_id: str, db: Session = Depends(get_db)):
    exam = db.scalar(select(Exam).where(Exam.id == exam_id, Exam.is_active == True))
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exame não encontrado")

    booklets = db.scalars(select(Booklet).where(Booklet.exam_id == exam_id).order_by(Booklet.day, Booklet.color)).all()
    results = []
    for booklet in booklets:
        paper_url = None
        color_clean = booklet.color.upper()
        if exam.application == "regular":
            if exam.year == 2025:
                number = REGULAR_2025_PAPERS.get((booklet.day, color_clean))
            elif exam.year == 2024:
                number = REGULAR_2024_PAPERS.get((booklet.day, color_clean))
            else:
                number = PAST_PAPERS.get((booklet.day, color_clean))

            if number is not None:
                paper_url = (
                    "https://download.inep.gov.br/enem/provas_e_gabaritos/"
                    f"{exam.year}_PV_impresso_D{booklet.day}_CD{number}.pdf"
                )
        pdf_download_url = f"/v1/exams/booklets/{booklet.id}/pdf"
        results.append(
            BookletOut.model_validate(booklet).model_copy(
                update={"paper_url": paper_url, "pdf_download_url": pdf_download_url}
            )
        )
    return results


@router.get("/booklets/{booklet_id}/items", response_model=list[BookletItemOut])
def get_booklet_items(booklet_id: str, db: Session = Depends(get_db)):
    booklet = db.scalar(
        select(Booklet).join(Exam, Booklet.exam_id == Exam.id).where(
            Booklet.id == booklet_id, Exam.is_active == True
        )
    )
    if not booklet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caderno não encontrado")

    query = (
        select(BookletItem, Item.area)
        .join(Item, BookletItem.item_id == Item.id)
        .where(BookletItem.booklet_id == booklet_id)
        .order_by(BookletItem.physical_position)
    )
    rows = db.execute(query).all()
    results = []
    for bi, area in rows:
        results.append(
            BookletItemOut(
                id=bi.id,
                physical_position=bi.physical_position,
                area=area,
                annulled=bi.answer_key == "*",
            )
        )
    return results


@router.get("/booklets/{booklet_id}/pdf")
def get_booklet_pdf(booklet_id: str, db: Session = Depends(get_db)):
    booklet = db.scalar(
        select(Booklet).join(Exam, Booklet.exam_id == Exam.id).where(
            Booklet.id == booklet_id, Exam.is_active == True
        )
    )
    if not booklet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caderno não encontrado")

    exam = booklet.exam
    color_clean = booklet.color.upper()
    number = None
    if exam.year == 2025:
        number = REGULAR_2025_PAPERS.get((booklet.day, color_clean))
    elif exam.year == 2024:
        number = REGULAR_2024_PAPERS.get((booklet.day, color_clean))
    else:
        number = PAST_PAPERS.get((booklet.day, color_clean))

    filename = f"{exam.year}_PV_impresso_D{booklet.day}_CD{number}.pdf" if number else None
    if filename:
        local_path = BOOKLETS_DIR / filename
        if local_path.is_file():
            return FileResponse(
                path=str(local_path),
                media_type="application/pdf",
                filename=filename,
            )
        return RedirectResponse(url=f"https://download.inep.gov.br/enem/provas_e_gabaritos/{filename}")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF do caderno não encontrado")
