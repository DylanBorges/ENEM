"""Public catalog of items with published Inep microdata parameters."""

from collections import defaultdict
from math import ceil
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.exams import _paper_location
from app.db.session import get_db
from app.models.calibration import CalibrationRun, ItemParameterModel
from app.models.exam import Booklet, BookletItem, Exam, Item

router = APIRouter(prefix="/questions", tags=["questions"])

AREA_NAMES = {
    "LC": "Linguagens",
    "CH": "Ciências Humanas",
    "CN": "Ciências da Natureza",
    "MT": "Matemática",
}
DIFFICULTY_NAMES = ("facil", "media", "dificil")
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PAGE_MAP_FILE = Path(__file__).resolve().parents[2] / "db/question_pages.json"
PAGE_MAP = json.loads(PAGE_MAP_FILE.read_text(encoding="utf-8")) if PAGE_MAP_FILE.is_file() else {}


def _subject(area: str, booklet: Booklet, position: int) -> str | None:
    # Only classifications directly established by the exam structure are used.
    # A skill code does not uniquely identify Biology/Physics/Chemistry etc.
    if area == "MT":
        return "Matemática"
    if area == "LC" and position <= 5:
        return {"INGLES": "Inglês", "ESPANHOL": "Espanhol"}.get(booklet.language or "")
    return None


def _difficulty_cutoffs(values: list[float]) -> tuple[float, float]:
    ordered = sorted(values)
    return ordered[ceil(len(ordered) / 3) - 1], ordered[ceil(2 * len(ordered) / 3) - 1]


def _build_catalog(db: Session) -> list[dict]:
    """Only expose items backed by a published, nonempty calibration."""
    rows = db.execute(
        select(Item, Exam, ItemParameterModel, CalibrationRun)
        .join(Exam, Item.exam_id == Exam.id)
        .join(ItemParameterModel, ItemParameterModel.item_id == Item.id)
        .join(CalibrationRun, ItemParameterModel.calibration_run_id == CalibrationRun.id)
        .where(
            Exam.is_active.is_(True),
            CalibrationRun.status == "PUBLISHED",
            CalibrationRun.dataset_sha256 != EMPTY_SHA256,
            CalibrationRun.exam_year == Exam.year,
            CalibrationRun.application == Exam.application,
            CalibrationRun.area == Item.area,
            ItemParameterModel.status == "ACTIVE",
        )
    ).all()

    latest = {}
    for item, exam, param, run in rows:
        existing = latest.get(item.id)
        if existing is None or (run.created_at, run.id) > (existing[3].created_at, existing[3].id):
            latest[item.id] = (item, exam, param, run)

    mappings = db.execute(
        select(BookletItem, Booklet)
        .join(Booklet, BookletItem.booklet_id == Booklet.id)
        .where(BookletItem.item_id.in_(latest.keys()))
    ).all() if latest else []
    by_item = defaultdict(list)
    for mapping, booklet in mappings:
        by_item[mapping.item_id].append((mapping, booklet))

    grouped_b = defaultdict(list)
    for item, exam, param, _ in latest.values():
        grouped_b[(exam.year, item.area)].append(param.b)
    cutoffs = {key: _difficulty_cutoffs(values) for key, values in grouped_b.items()}

    catalog = []
    for item, exam, param, run in latest.values():
        choices = by_item.get(item.id, [])
        if not choices:
            continue
        mapping, booklet = min(
            choices,
            key=lambda pair: (pair[1].color.upper() != "AZUL", pair[1].language != "INGLES", pair[1].day, pair[0].physical_position),
        )
        lower, upper = cutoffs[(exam.year, item.area)]
        level = "facil" if param.b <= lower else "media" if param.b <= upper else "dificil"
        location = _paper_location(exam, booklet)
        page_key = f"ES-{mapping.physical_position}" if booklet.language == "ESPANHOL" and mapping.physical_position <= 5 else str(mapping.physical_position)
        paper_page = PAGE_MAP.get(f"{exam.year}-{booklet.day}", {}).get(page_key)
        catalog.append({
            "id": item.id,
            "year": exam.year,
            "day": booklet.day,
            "area": item.area,
            "area_name": AREA_NAMES.get(item.area, item.area),
            "subject": _subject(item.area, booklet, mapping.physical_position),
            "position": mapping.physical_position,
            "booklet_color": booklet.color,
            "booklet_language": booklet.language,
            "official_item_code": item.official_item_code,
            "skill_code": item.skill_code,
            "difficulty": level,
            "parameter_b": round(param.b, 4),
            "calibration_id": run.calibration_id,
            "paper_url": location[1] if location else None,
            "paper_page": paper_page,
        })
    return catalog


@router.get("")
def list_questions(
    year: int | None = None,
    area: str | None = Query(default=None, pattern="^(LC|CH|CN|MT)$"),
    subject: str | None = None,
    difficulty: str | None = Query(default=None, pattern="^(facil|media|dificil)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    catalog = _build_catalog(db)

    subjects = sorted({question["subject"] for question in catalog if question["subject"]})
    years = sorted({question["year"] for question in catalog}, reverse=True)
    filtered = [question for question in catalog if
                (year is None or question["year"] == year)
                and (area is None or question["area"] == area)
                and (subject is None or question["subject"] == subject)
                and (difficulty is None or question["difficulty"] == difficulty)]
    filtered.sort(key=lambda q: (-q["year"], q["day"], q["position"], q["booklet_language"] == "ESPANHOL", q["official_item_code"] or ""))
    start = (page - 1) * page_size
    return {
        "items": filtered[start:start + page_size],
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
        "years": years,
        "subjects": subjects,
        "classified_count": sum(question["subject"] is not None for question in catalog),
        "analyzed_count": len(catalog),
        "difficulty_note": "Faixas relativas por edição e área, divididas em tercis do parâmetro b dos microdados do Inep; não são categorias oficiais.",
    }


@router.get("/{item_id}")
def get_question(item_id: str, db: Session = Depends(get_db)):
    question = next((q for q in _build_catalog(db) if q["id"] == item_id), None)
    if question is None:
        raise HTTPException(status_code=404, detail="Questão não encontrada no catálogo TRI")
    return question


class AnswerSubmission(BaseModel):
    answer: str = Field(pattern="^[ABCDE]$")


@router.post("/{item_id}/check")
def check_question_answer(item_id: str, submission: AnswerSubmission, db: Session = Depends(get_db)):
    question = get_question(item_id, db)
    mapping = db.scalar(
        select(BookletItem)
        .join(Booklet, BookletItem.booklet_id == Booklet.id)
        .where(
            BookletItem.item_id == item_id,
            Booklet.day == question["day"],
            Booklet.color == question["booklet_color"],
            BookletItem.physical_position == question["position"],
        )
    )
    if mapping is None:
        raise HTTPException(status_code=404, detail="Gabarito não encontrado")
    annulled = mapping.answer_key == "*"
    return {
        "item_id": item_id,
        "selected_answer": submission.answer,
        "correct_answer": None if annulled else mapping.answer_key.upper(),
        "correct": None if annulled else submission.answer == mapping.answer_key.upper(),
        "annulled": annulled,
    }
