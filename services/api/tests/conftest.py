import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import get_password_hash
from app.models.auth_institution import User, UserRole, Institution, Membership
from app.models.exam import Exam, Booklet, Item, BookletItem
from app.models.calibration import CalibrationRun, ItemParameterModel

# Banco de dados em memória isolado para testes
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seed_data(db_session):
    """Popula banco com exame de teste, caderno, itens parametrizados e calibração publicada."""
    # Usuário Estudante 1
    user1 = User(
        email="aluno1@escola.com",
        hashed_password=get_password_hash("senha12345"),
        full_name="Aluno Um",
        role=UserRole.STUDENT,
    )
    # Usuário Estudante 2 (outra instituição)
    user2 = User(
        email="aluno2@outra.com",
        hashed_password=get_password_hash("senha12345"),
        full_name="Aluno Dois",
        role=UserRole.STUDENT,
    )
    # Admin Instituição A
    admin_inst_a = User(
        email="gestor@escola-a.com",
        hashed_password=get_password_hash("senha12345"),
        full_name="Gestor Escola A",
        role=UserRole.INSTITUTION_ADMIN,
    )
    # Admin Plataforma
    platform_admin = User(
        email="admin@plataforma.com",
        hashed_password=get_password_hash("superadmin123"),
        full_name="Platform Admin",
        role=UserRole.PLATFORM_ADMIN,
    )
    db_session.add_all([user1, user2, admin_inst_a, platform_admin])
    db_session.flush()

    # Instituições
    inst_a = Institution(name="Colégio Alfa", slug="colegio-alfa")
    inst_b = Institution(name="Colégio Beta", slug="colegio-beta")
    db_session.add_all([inst_a, inst_b])
    db_session.flush()

    # Membros
    mem_admin_a = Membership(user_id=admin_inst_a.id, institution_id=inst_a.id, role=UserRole.INSTITUTION_ADMIN)
    mem_user1 = Membership(user_id=user1.id, institution_id=inst_a.id, role=UserRole.STUDENT)
    mem_user2 = Membership(user_id=user2.id, institution_id=inst_b.id, role=UserRole.STUDENT)
    db_session.add_all([mem_admin_a, mem_user1, mem_user2])

    # Exame ENEM 2025
    exam = Exam(year=2025, application="regular", title="ENEM 2025 Regular")
    db_session.add(exam)
    db_session.flush()

    booklet = Booklet(
        exam_id=exam.id,
        day=2,
        color="Azul",
        language=None,
        description="Caderno 5 Amarelo - Segundo Dia",
    )
    db_session.add(booklet)
    db_session.flush()

    # Calibração publicada para Matemática (MT)
    cal_mt = CalibrationRun(
        calibration_id="cal_2025_regular_mt_v1",
        exam_year=2025,
        application="regular",
        area="MT",
        irt_model="3PL",
        estimator="EAP",
        D=1.0,
        scale_alpha=510.0,
        scale_beta=99.5,
        minimum_coverage=0.7,
        dataset_sha256="hash_mt_2025",
        code_version="tri-core-0.1.0",
        status="PUBLISHED",
        official_algorithm=False,
    )
    db_session.add(cal_mt)
    db_session.flush()

    # 10 itens de teste para MT
    answer_keys = ["A", "B", "C", "D", "E", "A", "B", "C", "D", "E"]
    for i, ans in enumerate(answer_keys, start=1):
        item = Item(
            exam_id=exam.id,
            area="MT",
            official_item_code=f"ITEM_MT_{i}",
        )
        db_session.add(item)
        db_session.flush()

        bi = BookletItem(
            booklet_id=booklet.id,
            item_id=item.id,
            physical_position=i,
            answer_key=ans,
        )
        db_session.add(bi)

        param = ItemParameterModel(
            item_id=item.id,
            calibration_run_id=cal_mt.id,
            a=1.2,
            b=float(i - 5) * 0.4,
            c=0.2,
            D=1.0,
            status="ACTIVE",
        )
        db_session.add(param)

    db_session.commit()

    return {
        "user1": user1,
        "user2": user2,
        "admin_inst_a": admin_inst_a,
        "platform_admin": platform_admin,
        "inst_a": inst_a,
        "inst_b": inst_b,
        "exam": exam,
        "booklet": booklet,
        "cal_mt": cal_mt,
    }
