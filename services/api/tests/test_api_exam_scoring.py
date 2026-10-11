import io
import pytest


def test_complete_attempt_and_scoring_flow(client, seed_data):
    # 1. Login do Aluno 1
    login_res = client.post(
        "/v1/auth/login",
        json={"email": seed_data["user1"].email, "password": "senha12345"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Listagem de exames
    exams_res = client.get("/v1/exams", headers=headers)
    assert exams_res.status_code == 200
    assert len(exams_res.json()) >= 1
    booklets_res = client.get(f"/v1/exams/{seed_data['exam'].id}/booklets", headers=headers)
    assert booklets_res.status_code == 200
    assert booklets_res.json()[0]["paper_url"].endswith("2025_PV_impresso_D2_CD7.pdf")

    # 3. Criação de simulado / tentativa
    booklet_id = seed_data["booklet"].id
    att_res = client.post(
        "/v1/attempts",
        json={"booklet_id": booklet_id},
        headers=headers,
    )
    assert att_res.status_code == 201
    attempt_id = att_res.json()["id"]

    # 4. Envio de respostas manuais (8 certas, 2 erradas)
    # Gabarito: 1:A, 2:B, 3:C, 4:D, 5:E, 6:A, 7:B, 8:C, 9:D, 10:E
    responses_payload = {
        "responses": [
            {"position": 1, "answer": "A"},
            {"position": 2, "answer": "B"},
            {"position": 3, "answer": "C"},
            {"position": 4, "answer": "D"},
            {"position": 5, "answer": "E"},
            {"position": 6, "answer": "A"},
            {"position": 7, "answer": "B"},
            {"position": 8, "answer": "C"},
            {"position": 9, "answer": "A"},  # Errada (correta: D)
            {"position": 10, "answer": "B"}, # Errada (correta: E)
        ]
    }
    resp_res = client.put(
        f"/v1/attempts/{attempt_id}/responses",
        json=responses_payload,
        headers=headers,
    )
    assert resp_res.status_code == 200
    assert len(resp_res.json()) == 10

    # 5. Disparo do cálculo de nota TRI
    score_res = client.post(f"/v1/attempts/{attempt_id}/score", headers=headers)
    assert score_res.status_code == 200
    score_data = score_res.json()

    assert score_data["attempt_id"] == attempt_id
    assert len(score_data["areas"]) == 1
    area_mt = score_data["areas"][0]

    assert area_mt["area"] == "MT"
    assert area_mt["raw_correct"] == 8
    assert area_mt["answered_items"] == 10
    assert area_mt["coverage"] == 1.0
    assert area_mt["official"] is False  # CRÍTICO: Nunca é oficial
    assert area_mt["score_estimated"] > 0.0
    assert area_mt["credible_interval_95"][0] < area_mt["score_estimated"] < area_mt["credible_interval_95"][1]
    assert any("não oficial" in w.lower() for w in score_data["warnings"])

    # 6. Consulta subsequente do score persistido
    get_score_res = client.get(f"/v1/attempts/{attempt_id}/score", headers=headers)
    assert get_score_res.status_code == 200
    assert get_score_res.json()["areas"][0]["official"] is False


def test_scoring_fails_explicitly_when_calibration_missing(client, seed_data, db_session):
    """CRÍTICO: Sistema DEVE falhar explicitamente se não houver calibração publicada.

    Nunca deve inventar ou hardcodar parâmetros silenciosamente.
    """
    login_res = client.post(
        "/v1/auth/login",
        json={"email": seed_data["user1"].email, "password": "senha12345"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Remove calibração publicada de MT
    db_session.delete(seed_data["cal_mt"])
    db_session.commit()

    att_res = client.post(
        "/v1/attempts",
        json={"booklet_id": seed_data["booklet"].id},
        headers=headers,
    )
    attempt_id = att_res.json()["id"]

    # Tentativa de scoring
    score_res = client.post(f"/v1/attempts/{attempt_id}/score", headers=headers)
    assert score_res.status_code == 422
    assert "Calibração psicométrica ausente ou não publicada" in score_res.json()["detail"]


def test_inactive_exam_cannot_be_opened_or_scored(client, seed_data, db_session):
    token = client.post(
        "/v1/auth/login",
        json={"email": seed_data["user1"].email, "password": "senha12345"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    exam = seed_data["exam"]
    booklet = seed_data["booklet"]
    attempt_id = client.post(
        "/v1/attempts", json={"booklet_id": booklet.id}, headers=headers
    ).json()["id"]
    exam.is_active = False
    db_session.commit()

    assert client.get("/v1/exams", headers=headers).json() == []
    assert client.get(f"/v1/exams/{exam.id}/booklets", headers=headers).status_code == 404
    assert client.get(f"/v1/exams/booklets/{booklet.id}/items", headers=headers).status_code == 404
    assert client.post("/v1/attempts", json={"booklet_id": booklet.id}, headers=headers).status_code == 404
    assert client.post(f"/v1/attempts/{attempt_id}/score", headers=headers).status_code == 404


def test_2024_blue_booklet_links_to_matching_official_paper(client, seed_data, db_session):
    exam = seed_data["exam"]
    exam.year = 2024
    db_session.commit()

    response = client.get(f"/v1/exams/{exam.id}/booklets")

    assert response.status_code == 200
    assert response.json()[0]["paper_url"].endswith("2024_PV_impresso_D2_CD7.pdf")


def test_upload_answer_sheet_validation(client, seed_data):
    login_res = client.post(
        "/v1/auth/login",
        json={"email": seed_data["user1"].email, "password": "senha12345"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    att_res = client.post(
        "/v1/attempts",
        json={"booklet_id": seed_data["booklet"].id},
        headers=headers,
    )
    attempt_id = att_res.json()["id"]

    # 1. Upload inválido (.txt)
    txt_file = io.BytesIO(b"arquivo texto invalido")
    bad_res = client.post(
        f"/v1/attempts/{attempt_id}/answer-sheet",
        files={"file": ("cartao.txt", txt_file, "text/plain")},
        headers=headers,
    )
    assert bad_res.status_code == 400

    # 2. Upload válido (imagem PNG)
    png_file = io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimagebytes")
    good_res = client.post(
        f"/v1/attempts/{attempt_id}/answer-sheet",
        files={"file": ("cartao.png", png_file, "image/png")},
        headers=headers,
    )
    assert good_res.status_code == 200
    assert good_res.json()["status"] == "requires_confirmation"


def test_check_mark_responses_flow(client, seed_data):
    login_res = client.post(
        "/v1/auth/login",
        json={"email": seed_data["user1"].email, "password": "senha12345"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    att_res = client.post(
        "/v1/attempts",
        json={"booklet_id": seed_data["booklet"].id},
        headers=headers,
    )
    attempt_id = att_res.json()["id"]

    # Aluno apenas marcou check nas que acertou (posições 1 a 7 acertadas, 8 a 10 erradas)
    responses_payload = {
        "responses": [
            {"position": i, "is_correct": True} for i in range(1, 8)
        ] + [
            {"position": i, "is_correct": False} for i in range(8, 11)
        ]
    }
    resp_res = client.put(
        f"/v1/attempts/{attempt_id}/responses",
        json=responses_payload,
        headers=headers,
    )
    assert resp_res.status_code == 200
    saved = resp_res.json()
    assert len(saved) == 10
    assert sum(1 for r in saved if r["is_correct"] is True) == 7
    assert sum(1 for r in saved if r["is_correct"] is False) == 3

    score_res = client.post(f"/v1/attempts/{attempt_id}/score", headers=headers)
    assert score_res.status_code == 200
    area_score = score_res.json()["areas"][0]
    assert area_score["raw_correct"] == 7
