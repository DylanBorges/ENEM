from sqlalchemy import create_engine, func, select

from app.db.base import Base
from app.db.reference_seed import seed_reference_data_if_empty
from app.db.session import database_url
from app.models.auth_institution import User
from app.models.exam import Exam


def test_standard_postgres_url_uses_installed_driver():
    assert database_url("postgresql://user:secret@db.example/enem?sslmode=require") == (
        "postgresql+psycopg://user:secret@db.example/enem?sslmode=require"
    )
    assert database_url("postgres://user:secret@db.example/enem") == (
        "postgresql+psycopg://user:secret@db.example/enem"
    )
    assert database_url("sqlite:///local.db") == "sqlite:///local.db"
    engine = create_engine(database_url("postgresql://user:secret@db.example/enem"))
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"
    engine.dispose()


def test_reference_seed_is_idempotent_and_keeps_registered_users(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'persist.db'}")
    Base.metadata.create_all(engine)
    assert seed_reference_data_if_empty(engine) == 6632
    with engine.begin() as connection:
        connection.execute(
            User.__table__.insert().values(
                id="e6aa1536-0555-46a8-a277-0ff2c609a4b6",
                email="persist@example.com",
                hashed_password="test-only-hash",
                full_name="Conta persistente",
            )
        )
    engine.dispose()

    reopened = create_engine(f"sqlite:///{tmp_path / 'persist.db'}")
    assert seed_reference_data_if_empty(reopened) == 0
    with reopened.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(Exam)) == 9
        assert connection.scalar(select(func.count()).select_from(User)) == 1
    reopened.dispose()
