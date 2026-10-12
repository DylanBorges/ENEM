from app.models.calibration import CalibrationRun, ItemParameterModel
from app.models.exam import Booklet, BookletItem, Item


def test_catalog_filters_all_published_microdata_items_by_tri_difficulty(client, seed_data, db_session):
    response = client.get("/v1/questions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 10
    assert data["analyzed_count"] == 10
    assert data["classified_count"] == 10
    assert data["subjects"] == ["Matemática"]
    assert all(question["subject"] == "Matemática" for question in data["items"])
    assert all(question["paper_url"].endswith("2025_PV_impresso_D2_CD7.pdf") for question in data["items"])
    assert all(question["parameter_b"] is not None for question in data["items"])

    for level, expected in (("facil", 4), ("media", 3), ("dificil", 3)):
        filtered = client.get(f"/v1/questions?year=2025&area=MT&subject=Matem%C3%A1tica&difficulty={level}")
        assert filtered.status_code == 200
        assert filtered.json()["total"] == expected
        assert all(item["difficulty"] == level for item in filtered.json()["items"])

    assert client.get("/v1/questions?page=2&page_size=4").json()["items"][0]["position"] == 5
    assert client.get("/v1/questions?difficulty=inventada").status_code == 422


def test_catalog_does_not_invent_subject_or_publish_unparameterized_item(client, seed_data, db_session):
    exam = seed_data["exam"]
    booklet = Booklet(exam_id=exam.id, day=1, color="Azul", language="INGLES", description="Dia 1")
    db_session.add(booklet)
    db_session.flush()
    lc_calibration = CalibrationRun(
        calibration_id="lc_catalog_test", exam_year=2025, application="regular", area="LC",
        scale_alpha=500, scale_beta=100, dataset_sha256="verified_test_hash", code_version="test",
        status="PUBLISHED", official_algorithm=False,
    )
    db_session.add(lc_calibration)
    db_session.flush()
    for position in (1, 6):
        item = Item(exam_id=exam.id, area="LC", official_item_code=f"LC_{position}")
        db_session.add(item)
        db_session.flush()
        db_session.add(BookletItem(booklet_id=booklet.id, item_id=item.id, physical_position=position, answer_key="A"))
        db_session.add(ItemParameterModel(item_id=item.id, calibration_run_id=lc_calibration.id, a=1, b=1, c=0.2, status="ACTIVE"))
    missing = Item(exam_id=exam.id, area="LC", official_item_code="SEM_PARAMETRO")
    db_session.add(missing)
    db_session.flush()
    db_session.add(BookletItem(booklet_id=booklet.id, item_id=missing.id, physical_position=7, answer_key="A"))
    db_session.commit()

    data = client.get("/v1/questions?area=LC").json()
    assert data["total"] == 2
    by_position = {question["position"]: question for question in data["items"]}
    assert by_position[1]["subject"] == "Inglês"
    assert by_position[6]["subject"] is None
    assert client.get("/v1/questions?subject=Ingl%C3%AAs").json()["total"] == 1
