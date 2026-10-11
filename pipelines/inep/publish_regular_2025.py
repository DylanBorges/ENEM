"""Publica cadernos regulares de 2025 e estimador validado no banco local.

Não cria nem armazena enunciados. A API marca toda nota como não oficial.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from pipelines.inep.import_2025 import ROOT, sha256
from pipelines.inep.import_regular_2025 import OUTPUT as BOOKLETS_FILE
from pipelines.inep.validate_official_2025 import OUTPUT as VALIDATION_FILE
from pipelines.inep.download import verify_sha256

sys.path.insert(0, str(ROOT / "services/api"))
from app.models.exam import Exam, Booklet, Item, BookletItem  # noqa: E402
from app.models.calibration import CalibrationRun, ItemParameterModel  # noqa: E402
from app.models.attempt import Attempt  # noqa: E402

DEFAULT_DB = ROOT / "services/api/enem_intelligence.db"
RECEIPT = ROOT / "data/processed/2025/publicacao_banco_local.json"


def _read_sources(booklets_file: Path, validation_file: Path,
                  year: int, expected_booklets: int) -> tuple[dict, dict]:
    booklets = json.loads(booklets_file.read_text(encoding="utf-8"))
    validation = json.loads(validation_file.read_text(encoding="utf-8"))
    source_hash = booklets["source_microdados_sha256"]
    if (booklets["year"] != year or validation["year"] != year
            or source_hash != validation["source_microdados_sha256"] or len(source_hash) != 64):
        raise ValueError("Manifestos de cadernos e validação apontam para fontes diferentes")
    archive = ROOT / f"data/raw/{year}/microdados_enem_{year}.zip"
    if not verify_sha256(str(archive), source_hash):
        raise ValueError("Arquivo oficial difere do pacote validado")
    if booklets["booklet_count"] != expected_booklets or len(booklets["booklets"]) != expected_booklets:
        raise ValueError("Quantidade de cadernos não corresponde ao mapeamento esperado")
    for booklet in booklets["booklets"]:
        name = f"{year}_GB_impresso_D{booklet['day']}_CD{booklet['number']}.pdf"
        if sha256(ROOT / f"data/raw/{year}" / name) != booklet["official_key_sha256"]:
            raise ValueError(f"Gabarito oficial mudou desde o mapeamento: {name}")
    for area in ("LC", "CH", "CN", "MT"):
        result = validation["areas"][area]
        diagnostic = result["diagnostics"]
        if (not result["release_gate_passed"] or result["holdout_count"] < 1000
                or diagnostic["errors_over_100"] or diagnostic["p99_absolute_error"] > 35):
            raise ValueError(f"Validação insuficiente para publicação: {area}")
    return booklets, validation


def _backup_sqlite(path: Path, year: int) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"Banco local não encontrado: {path}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = ROOT / f"data/processed/{year}" / f"backup-antes-publicacao-{stamp}.db"
    backup.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    return backup


def _selected_rows(booklet: dict, language: str | None) -> list[dict]:
    rows = []
    for area, data in booklet["areas"].items():
        for item in data["items"]:
            if area != "LC" or item["language"] is None or item["language"] == language:
                rows.append(item)
    expected = set(range(1, 91)) if booklet["day"] == 1 else set(range(91, 181))
    positions = [item["position"] for item in rows]
    if len(rows) != 90 or set(positions) != expected:
        raise ValueError(f"Caderno {booklet['number']} com posições incompletas ou duplicadas")
    return sorted(rows, key=lambda item: item["position"])


def publish(db_path: Path = DEFAULT_DB, booklets_file: Path = BOOKLETS_FILE,
            validation_file: Path = VALIDATION_FILE, receipt_file: Path = RECEIPT,
            year: int = 2025, expected_booklets: int = 8) -> dict:
    booklets, validation = _read_sources(booklets_file, validation_file, year, expected_booklets)
    source_hash = booklets["source_microdados_sha256"]
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    with Session(engine) as session:
        existing = session.scalar(select(Exam).where(Exam.year == year, Exam.application == "regular"))
        if existing and existing.is_active:
            raise ValueError(f"Já existe exame {year} regular ativo; revisão manual necessária")
        if existing:
            if year != 2025:
                raise ValueError("Substituição automática permitida apenas para o seed antigo de 2025")
            old_booklets = list(existing.booklets)
            if any(session.scalar(select(Attempt.id).where(Attempt.booklet_id == booklet.id))
                   for booklet in old_booklets):
                raise ValueError("O exame anterior possui tentativas; substituição recusada")
            if not all((item.official_item_code or "").startswith("ITEM_2025_MT_")
                       for item in existing.items):
                raise ValueError("Exame inativo não corresponde ao seed antigo conhecido")
        old_runs = session.scalars(select(CalibrationRun).where(
            CalibrationRun.exam_year == year, CalibrationRun.application == "regular",
            CalibrationRun.status == "PUBLISHED")).all()
        if old_runs:
            raise ValueError(f"Há calibração publicada para {year}; revisão manual necessária")
    backup = _backup_sqlite(db_path, year)
    with Session(engine) as session, session.begin():
        existing = session.scalar(select(Exam).where(Exam.year == year, Exam.application == "regular"))
        if existing:
            session.delete(existing)
            session.flush()
        exam = Exam(year=year, application="regular",
                    title=f"ENEM {year} — Aplicação regular (Inep)", is_active=True)
        session.add(exam)
        session.flush()
        runs = {}
        for area, result in validation["areas"].items():
            run = CalibrationRun(
                calibration_id=f"enem-{year}-regular-{area.lower()}-inep-{source_hash[:12]}",
                exam_year=year, application="regular", area=area,
                irt_model="3PL", estimator="EAP", D=1.0,
                scale_alpha=result["scale_alpha"], scale_beta=result["scale_beta"],
                minimum_coverage=0.7, dataset_sha256=source_hash,
                code_version="tri-core-0.1.0", status="PUBLISHED",
                official_algorithm=False,
                validation_metrics={**result["metrics"], "diagnostics": result["diagnostics"],
                                    "link_count": result["link_count"],
                                    "sampling": validation["sampling"]},
            )
            session.add(run)
            runs[area] = run
        session.flush()
        items_by_identity = {}
        for booklet_data in booklets["booklets"]:
            languages = ("ingles", "espanhol") if booklet_data["day"] == 1 else (None,)
            for language in languages:
                booklet = Booklet(
                    exam_id=exam.id, day=booklet_data["day"],
                    color=booklet_data["color"].title(),
                    language=language.upper() if language else None,
                    description=f"Caderno {booklet_data['number']} — {booklet_data['color'].title()}"
                                + (f" — {language.title()}" if language else ""),
                )
                session.add(booklet)
                session.flush()
                for source_item in _selected_rows(booklet_data, language):
                    identity = (source_item["area"], source_item["inep_item_id"])
                    item = items_by_identity.get(identity)
                    if item is None:
                        item = Item(exam_id=exam.id, area=source_item["area"],
                                    official_item_code=str(source_item["inep_item_id"]),
                                    skill_code=str(source_item["skill_code"]))
                        session.add(item)
                        session.flush()
                        items_by_identity[identity] = item
                        params = source_item["parameters"]
                        if params is not None:
                            session.add(ItemParameterModel(
                                item_id=item.id, calibration_run_id=runs[source_item["area"]].id,
                                a=params["a"], b=params["b"], c=params["c"], D=1.0,
                                status="ACTIVE",
                            ))
                    session.add(BookletItem(
                        booklet_id=booklet.id, item_id=item.id,
                        physical_position=source_item["position"],
                        answer_key=source_item["answer"] or "*",
                    ))
        if len(items_by_identity) != booklets["distinct_inep_items"]:
            raise ValueError("Contagem de itens distinta do mapeamento auditado")
        exam_id = exam.id
    receipt = {
        "exam_id": exam_id, "source_microdados_sha256": source_hash,
        "booklet_count": sum(2 if booklet["day"] == 1 else 1 for booklet in booklets["booklets"]),
        "distinct_items": len(items_by_identity),
        "official": False,
        "disclaimer": "Notas estimadas por método independente; não são notas oficiais do Inep.",
        "backup": str(backup),
    }
    receipt_file.parent.mkdir(parents=True, exist_ok=True)
    receipt_file.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    print(json.dumps(publish(), ensure_ascii=False))
