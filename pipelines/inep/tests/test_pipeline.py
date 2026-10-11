import numpy as np
import pytest

from pipelines.inep.normalize import parse_responses_and_keys
from pipelines.inep.import_2025 import normalize_item, select_booklets
from pipelines.inep.import_regular_2025 import parse_key_text
from pipelines.inep.validate_official_2025 import eap_batch
from tri_core.eap import eap
from pipelines.inep.calibrate import run_full_calibration_pipeline
from pipelines.inep.validate import check_release_gate
from tri_core.models import ItemParameter
from tri_core.three_pl import probability_3pl


def test_parse_responses_and_keys():
    res = parse_responses_and_keys("ABCDE", "AB*DE")
    # Questão anulada é ausente para estimativa, não acerto.
    assert res == [1, 1, None, 1, 1]

    res_err = parse_responses_and_keys("AAAAA", "ABCDE")
    assert res_err == [1, 0, 0, 0, 0]

    with pytest.raises(ValueError):
        parse_responses_and_keys("AB", "ABCDE")


def test_2025_selection_requires_complete_exact_key(monkeypatch):
    from pipelines.inep import import_2025

    monkeypatch.setattr(import_2025, "AREA_RANGES", {"CN": range(91, 93), "MT": range(136, 138)})
    rows = [
        {"SG_AREA": area, "TX_COR": "AMARELA", "CO_PROVA": code,
         "CO_POSICAO": str(position), "TX_GABARITO": answer}
        for area, code, answers in (("CN", "1484", [(91, "A"), (92, "X")]),
                                     ("MT", "1472", [(136, "B"), (137, "C")]))
        for position, answer in answers
    ]
    assert {area: len(booklet) for area, booklet in select_booklets(
        rows, {91: "A", 92: "X", 136: "B", 137: "C"}
    ).items()} == {"CN": 2, "MT": 2}
    rows[1]["TX_GABARITO"] = "B"
    with pytest.raises(ValueError):
        select_booklets(rows, {91: "A", 92: "X", 136: "B", 137: "C"})


def test_2025_excluded_item_never_gets_parameters():
    row = {"TX_GABARITO": "B", "IN_ITEM_ABAN": "1",
           "NU_PARAM_A": "", "NU_PARAM_B": "", "NU_PARAM_C": "",
           "CO_POSICAO": "127", "SG_AREA": "CN", "CO_PROVA": "1484",
           "CO_ITEM": "96748", "TX_MOTIVO_ABAN": "Problema de convergência",
           "CO_HABILIDADE": "25"}
    item = normalize_item(row)
    assert item["answer"] == "B"
    assert item["excluded_from_psychometrics"] is True
    assert item["parameters"] is None
    row["NU_PARAM_A"] = "1.0"
    with pytest.raises(ValueError):
        normalize_item(row)


def test_regular_2025_first_day_key_preserves_both_languages():
    text = "\n".join([f"{position} A B" for position in range(1, 6)]
                     + [f"{position} C" for position in range(6, 91)])
    key = parse_key_text(text, 1)
    assert len(key) == 95
    assert key[(1, "0")] == "A" and key[(1, "1")] == "B"
    assert key[(6, "")] == "C"
    with pytest.raises(ValueError):
        parse_key_text(text.replace("90 C", ""), 1)


def test_batch_eap_matches_core_single_pattern():
    items = [{"parameters": {"a": 1.2, "b": -0.4, "c": 0.2}},
             {"parameters": {"a": 0.8, "b": 0.5, "c": 0.15}}]
    response = np.array([[1, 0]], dtype=float)
    expected = eap([1, 0], [ItemParameter(**item["parameters"]) for item in items]).theta
    assert eap_batch(response, items)[0] == pytest.approx(expected, abs=1e-10)


def test_full_inep_calibration_and_release_gate():
    np.random.seed(42)
    n_examinees = 200
    n_items = 10

    # Simula dados com 10 itens
    thetas = np.random.normal(0, 1, n_examinees)
    items = [ItemParameter(a=1.4, b=float(i - 4.5) * 0.5, c=0.2) for i in range(n_items)]

    responses = np.zeros((n_examinees, n_items), dtype=np.int32)
    for j, itm in enumerate(items):
        p = probability_3pl(thetas, itm)
        responses[:, j] = (np.random.uniform(0, 1, n_examinees) < p).astype(np.int32)

    # Notas oficiais simuladas com erro pequeno
    official_scores = 500.0 + 100.0 * thetas + np.random.normal(0, 5, n_examinees)

    cal_version, meta = run_full_calibration_pipeline(
        response_matrix=responses,
        official_scores=official_scores,
        exam_year=2025,
        area="MT",
    )

    assert cal_version.exam_year == 2025
    assert cal_version.scale_beta > 0
    assert cal_version.official_algorithm is False
    assert cal_version.status == "DRAFT"
    assert "mae" in cal_version.validation_metrics

    # Release gate: aprova com tolerância ajustada ao tamanho do teste sintético
    gate_res = check_release_gate(cal_version, max_acceptable_mae=75.0, min_acceptable_correlation=0.70)
    assert gate_res["passed"] is True
    assert gate_res["status"] == "APPROVED_FOR_PUBLICATION"
