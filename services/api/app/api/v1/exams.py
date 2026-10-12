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

INEP_PAPERS_BASE = "https://download.inep.gov.br/enem/provas_e_gabaritos"
INEP_ARCHIVE_BASE = "https://download.inep.gov.br/educacao_basica/enem/provas"


def _paper_location(exam: Exam, booklet: Booklet) -> tuple[str, str] | None:
    if exam.application != "regular":
        return None

    color = booklet.color.upper()
    if exam.year == 2025:
        number = REGULAR_2025_PAPERS.get((booklet.day, color))
    elif exam.year == 2024:
        number = REGULAR_2024_PAPERS.get((booklet.day, color))
    else:
        number = PAST_PAPERS.get((booklet.day, color))
    if number is None:
        return None

    filename = f"{exam.year}_PV_impresso_D{booklet.day}_CD{number}.pdf"
    if exam.year == 2018 and booklet.day == 2 and number == 5:
        official_url = f"{INEP_ARCHIVE_BASE}/2018/2DIA_05_AMARELO_BAIXA.pdf"
    elif exam.year <= 2019:
        official_url = f"{INEP_ARCHIVE_BASE}/{exam.year}/{filename}"
    else:
        official_url = f"{INEP_PAPERS_BASE}/{filename}"
    return filename, official_url

def _find_booklets_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        cand = parent / "data/booklets"
        if cand.is_dir():
            return cand
    return Path("data/booklets")


BOOKLETS_DIR = _find_booklets_dir()


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
        location = _paper_location(exam, booklet)
        paper_url = location[1] if location else None
        pdf_download_url = f"/v1/exams/booklets/{booklet.id}/pdf" if location else None
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
    location = _paper_location(exam, booklet)
    if location:
        filename, official_url = location
        local_path = BOOKLETS_DIR / filename
        if local_path.is_file():
            return FileResponse(
                path=str(local_path),
                media_type="application/pdf",
                filename=filename,
            )
        return RedirectResponse(url=official_url)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF do caderno não encontrado")
