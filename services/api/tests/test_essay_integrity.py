import json

import pytest

from app.services.gemini_essay_service import (
    AssessmentUnavailable, InvalidAssessment, evaluate_essay_with_gemini,
    parse_assessment,
)


def assessment(text="Trecho real do estudante."):
    return json.dumps({
        "total_score": 600,
        "competencies": [
            {"code": f"C{i}", "predicted_score": 120, "confidence": 0.7,
             "feedback": "Análise pedagógica.", "evidence_spans": [text]}
            for i in range(1, 6)
        ],
    })


def test_assessment_requires_five_valid_scores_and_real_evidence():
    result = parse_assessment(assessment(), "Trecho real do estudante.", "test-model")
    assert result.total_score == 600
    assert result.official is False

    with pytest.raises(InvalidAssessment):
        parse_assessment(assessment(), "Outro texto.", "test-model")
    payload = json.loads(assessment())
    payload["competencies"][0]["predicted_score"] = 123
    with pytest.raises(InvalidAssessment):
        parse_assessment(json.dumps(payload), "Trecho real do estudante.", "test-model")
    with pytest.raises(InvalidAssessment):
        parse_assessment("not JSON", "Trecho real do estudante.", "test-model")


def test_api_does_not_fabricate_grade_without_provider(client, seed_data, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    login = client.post("/v1/auth/login", json={"email": seed_data["user1"].email, "password": "senha12345"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = client.post("/v1/essays", headers=headers, json={"topic": "Tema de teste", "text": "Texto para avaliação. " * 10})
    assert created.status_code == 201
    response = client.post(f"/v1/essays/{created.json()['id']}/pregrade", headers=headers)
    assert response.status_code == 503


@pytest.mark.parametrize("provider_code,expected", [
    (404, "modelo Gemini não está disponível"),
    (429, "cota do Gemini foi atingida"),
    (403, "não tem permissão"),
])
def test_provider_errors_are_actionable_without_exposing_submission(
    monkeypatch, provider_code, expected
):
    from google import genai
    from google.genai.errors import ClientError
    from app.core.config import settings

    class FailingModels:
        def generate_content(self, **kwargs):
            raise ClientError(provider_code, {"error": {"code": provider_code,
                "message": "Texto secreto da redação", "status": "ERROR"}})

    class FailingClient:
        def __init__(self, **kwargs):
            self.models = FailingModels()

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(genai, "Client", FailingClient)

    with pytest.raises(AssessmentUnavailable) as failure:
        evaluate_essay_with_gemini("Tema", "Texto secreto da redação")
    assert expected in str(failure.value)
    assert "Texto secreto da redação" not in str(failure.value)


def test_admin_cannot_publish_fabricated_calibration(client, seed_data):
    login = client.post("/v1/auth/login", json={"email": seed_data["platform_admin"].email, "password": "superadmin123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    imported = client.post("/v1/admin/inep/imports", headers=headers, json={"year": 2025})
    assert imported.status_code == 501


def test_empty_dataset_hash_cannot_score_or_appear_as_available(client, seed_data, db_session):
    seed_data["cal_mt"].dataset_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    db_session.commit()
    assert client.get("/v1/exams").json() == []
    login = client.post("/v1/auth/login", json={"email": seed_data["user1"].email, "password": "senha12345"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    attempt = client.post("/v1/attempts", headers=headers, json={"booklet_id": seed_data["booklet"].id})
    response = client.post(f"/v1/attempts/{attempt.json()['id']}/score", headers=headers)
    assert response.status_code == 422
