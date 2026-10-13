import json
from pathlib import Path

from pipelines.inep.classify_subject import classify_subject


ROOT = Path(__file__).resolve().parents[3]
CONTENT = ROOT / "services/api/app/db/question_content.json"
IMAGES = ROOT / "apps/web/public"


def test_published_questions_have_complete_native_content_and_local_figures():
    records = json.loads(CONTENT.read_text(encoding="utf-8"))
    assert len(records) >= 1600
    for question_key, record in records.items():
        assert record["official_item_code"], question_key
        assert record["answer_key"] in "ABCDE*", question_key
        assert record["blocks"], question_key
        assert [option["letter"] for option in record["alternatives"]] == list("ABCDE"), question_key
        for option in record["alternatives"]:
            assert option["text"] or option["image"], question_key
        images = [block["value"] for block in record["blocks"] if block["type"] == "image"]
        images.extend(option["image"] for option in record["alternatives"] if option["image"])
        for image in images:
            assert image.startswith("/question-images/"), question_key
            assert (IMAGES / image.lstrip("/")).is_file(), question_key


def test_subject_hints_are_specific_but_abstain_when_ambiguous():
    assert classify_subject("CN", "A fotossíntese em células vegetais é influenciada pelo ecossistema.", 100, None) == "Biologia"
    assert classify_subject("CH", "A filosofia de Platão e Aristóteles discute a ética.", 60, None) == "Filosofia"
    assert classify_subject("LC", "O narrador do romance descreve o personagem.", 20, None) == "Literatura"
    assert classify_subject("CN", "Observe a situação apresentada.", 100, None) is None
