"""Load the checked-in reference catalog into SQLite or PostgreSQL."""

from datetime import datetime
import json
from pathlib import Path
import sqlite3

from sqlalchemy import Boolean, DateTime, JSON, create_engine, insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.exam import Exam


SEED_FILE = Path(__file__).with_name("reference_seed.sql")
SEED_TABLES = (
    "institutions", "exams", "booklets", "items", "booklet_items",
    "calibration_runs", "item_parameters", "essay_rubrics", "essay_competencies",
)


def seed_reference_data_if_empty(engine: Engine) -> int:
    if not SEED_FILE.is_file():
        raise FileNotFoundError(SEED_FILE)

    with engine.begin() as target:
        if target.scalar(select(Exam.id).limit(1)) is not None:
            return 0

        source = sqlite3.connect(":memory:")
        source.row_factory = sqlite3.Row
        source_engine = create_engine("sqlite://", creator=lambda: source, poolclass=StaticPool)
        try:
            # The checked-in seed is SQLite SQL. Staging it in memory lets the
            # same verified records be loaded into either supported database.
            Base.metadata.create_all(source_engine)
            source.executescript(SEED_FILE.read_text(encoding="utf-8"))

            total = 0
            for name in SEED_TABLES:
                table = Base.metadata.tables[name]
                rows = source.execute(f'SELECT * FROM "{name}"').fetchall()
                for start in range(0, len(rows), 200):
                    batch = []
                    for row in rows[start:start + 200]:
                        values = {}
                        for column in table.columns:
                            value = row[column.name]
                            if value is not None and isinstance(column.type, DateTime):
                                value = datetime.fromisoformat(value)
                            elif value is not None and isinstance(column.type, Boolean):
                                value = bool(value)
                            elif value is not None and isinstance(column.type, JSON):
                                value = json.loads(value)
                            values[column.name] = value
                        batch.append(values)
                    target.execute(insert(table), batch)
                total += len(rows)
            return total
        finally:
            source_engine.dispose()
            source.close()
