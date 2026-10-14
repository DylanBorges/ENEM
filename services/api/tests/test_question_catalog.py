from app.models.calibration import CalibrationRun, ItemParameterModel
from app.models.exam import Booklet, BookletItem, Item
from app.api.v1.questions import CONTENT_MAP, _content_for_question
from app.api.v1 import questions as questions_api


def test_native_content_is_bound_to_the_official_item_code_and_area():
    content = CONTENT_MAP["2025-1-INGLES"]
    question = {"year": 2025, "position": 1, "booklet_language": "INGLES",
                "area": "LC", "official_item_code": content["official_item_code"]}
    assert _content_for_question(question)["alternatives"][0]["letter"] == "A"
    assert _content_for_question({**question, "official_item_code": "OTHER"}) is None
    assert _content_for_question({**question, "area": "MT"}) is None


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


def test_question_detail_and_answer_use_the_matching_official_key(client, seed_data, db_session):
    item_id = client.get("/v1/questions?page_size=1").json()["items"][0]["id"]
    detail = client.get(f"/v1/questions/{item_id}")
    assert detail.status_code == 200
    assert detail.json()["paper_url"].endswith("2025_PV_impresso_D2_CD7.pdf")

    wrong = client.post(f"/v1/questions/{item_id}/check", json={"answer": "B"})
    assert wrong.status_code == 200
    assert wrong.json() == {
        "item_id": item_id, "selected_answer": "B", "correct_answer": "A",
        "correct": False, "annulled": False,
    }
    right = client.post(f"/v1/questions/{item_id}/check", json={"answer": "A"})
    assert right.json()["correct"] is True
    assert client.post(f"/v1/questions/{item_id}/check", json={"answer": "Z"}).status_code == 422
    assert client.get("/v1/questions/nonexistent").status_code == 404
    assert client.post("/v1/questions/nonexistent/check", json={"answer": "A"}).status_code == 404

    # An item without published calibration cannot be used as an answer oracle.
    private = Item(exam_id=seed_data["exam"].id, area="MT", official_item_code="UNPUBLISHED")
    db_session.add(private)
    db_session.flush()
    db_session.add(BookletItem(booklet_id=seed_data["booklet"].id, item_id=private.id, physical_position=11, answer_key="E"))
    db_session.commit()
    assert client.post(f"/v1/questions/{private.id}/check", json={"answer": "E"}).status_code == 404


def test_native_question_detail_and_answer_follow_the_displayed_booklet(client, seed_data, db_session):
    content = CONTENT_MAP["2025-136-NONE"]
    item = Item(exam_id=seed_data["exam"].id, area="MT", official_item_code=content["official_item_code"])
    db_session.add(item)
    db_session.flush()
    wrong_local_key = next(letter for letter in "ABCDE" if letter != content["answer_key"])
    db_session.add(BookletItem(booklet_id=seed_data["booklet"].id, item_id=item.id,
                               physical_position=136, answer_key=wrong_local_key))
    db_session.add(ItemParameterModel(item_id=item.id, calibration_run_id=seed_data["cal_mt"].id,
                                      a=1.2, b=0.2, c=0.2, status="ACTIVE"))
    db_session.commit()

    detail = client.get(f"/v1/questions/{item.id}").json()
    assert detail["content_available"] is True
    assert detail["blocks"]
    assert [choice["letter"] for choice in detail["alternatives"]] == list("ABCDE")
    assert client.post(f"/v1/questions/{item.id}/check", json={"answer": content["answer_key"]}).json()["correct"] is True


def test_question_arrows_follow_catalog_filters_and_skip_unreadable_items(client, monkeypatch):
    catalog = [
        {"id": item_id, "year": 2025, "day": 1, "position": position,
         "area": "LC", "subject": subject, "difficulty": "facil",
         "booklet_language": "INGLES", "official_item_code": item_id,
         "content_available": readable}
        for item_id, position, subject, readable in (
            ("c", 3, "Inglês", True), ("b", 2, "Inglês", False),
            ("d", 4, "Português", True), ("a", 1, "Inglês", True),
        )
    ]
    monkeypatch.setattr(questions_api, "_build_catalog", lambda db: catalog)

    first = client.get("/v1/questions/a/neighbors?year=2025&area=LC&subject=Ingl%C3%AAs&difficulty=facil")
    assert first.status_code == 200
    assert first.json() == {"previous": None, "next": {"id": "c", "position": 3}}
    last = client.get("/v1/questions/c/neighbors?subject=Ingl%C3%AAs")
    assert last.json() == {"previous": {"id": "a", "position": 1}, "next": None}
    assert client.get("/v1/questions/c/neighbors").json()["next"] == {"id": "d", "position": 4}
    assert client.get("/v1/questions/b/neighbors").json() == {"previous": None, "next": None}
    assert client.get("/v1/questions/unpublished/neighbors").status_code == 404
    assert client.get("/v1/questions/a/neighbors?difficulty=unknown").status_code == 422
