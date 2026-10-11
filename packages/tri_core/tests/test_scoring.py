import pytest
import numpy as np

from tri_core.models import (
    ItemParameter,
    PriorConfig,
    CalibrationVersion,
    EAPResult,
    ScoreEstimateOutput,
)
from tri_core.three_pl import probability_3pl, log_likelihood
from tri_core.eap import eap, score_pattern
from tri_core.linking import LinearScale, fit_linear_scale


def test_1_probability_3pl_bounded_between_c_and_one():
    """1. P(theta) fica entre c e 1."""
    item = ItemParameter(a=1.5, b=0.5, c=0.2, D=1.0)
    thetas = np.linspace(-10.0, 10.0, 100)
    probs = probability_3pl(thetas, item)

    assert np.all(probs >= item.c)
    assert np.all(probs <= 1.0)


def test_2_probability_strictly_increasing_with_positive_a():
    """2. Para a>0, P cresce com theta."""
    item = ItemParameter(a=1.2, b=0.0, c=0.2, D=1.0)
    thetas = np.array([-3.0, -1.0, 0.0, 1.0, 3.0])
    probs = probability_3pl(thetas, item)

    for i in range(len(probs) - 1):
        assert probs[i] < probs[i + 1]


def test_3_probability_at_theta_equal_b():
    """3. Em theta=b: P = c + (1-c)/2."""
    for b_val in [-2.0, 0.0, 1.5]:
        item = ItemParameter(a=1.8, b=b_val, c=0.25, D=1.0)
        p_at_b = probability_3pl(np.array([b_val]), item)[0]
        expected = item.c + (1.0 - item.c) * 0.5
        assert np.isclose(p_at_b, expected, atol=1e-7)


def test_4_all_correct_produces_higher_theta_than_all_wrong():
    """4. all-correct produz theta maior que all-wrong no mesmo conjunto de itens."""
    items = [
        ItemParameter(a=1.0, b=-1.0, c=0.2),
        ItemParameter(a=1.3, b=0.0, c=0.2),
        ItemParameter(a=1.5, b=1.0, c=0.2),
    ]
    res_correct = eap([1, 1, 1], items)
    res_wrong = eap([0, 0, 0], items)

    assert res_correct.theta > res_wrong.theta


def test_5_posterior_sums_to_one():
    """5. posterior soma 1."""
    items = [
        ItemParameter(a=1.0, b=0.0, c=0.2),
        ItemParameter(a=1.5, b=0.5, c=0.2),
    ]
    res = eap([1, 0], items)
    assert np.isclose(np.sum(res.posterior), 1.0, atol=1e-9)


def test_6_posterior_sd_non_negative():
    """6. posterior_sd >= 0."""
    items = [
        ItemParameter(a=1.2, b=-0.2, c=0.2),
        ItemParameter(a=1.4, b=0.8, c=0.2),
    ]
    res = eap([1, 1], items)
    assert res.posterior_sd >= 0.0
    assert np.isfinite(res.posterior_sd)


def test_7_eap_is_finite_for_all_correct():
    """7. EAP é finito para all-correct."""
    items = [ItemParameter(a=1.2, b=float(i) - 2.0, c=0.2) for i in range(5)]
    res = eap([1] * 5, items)

    assert np.isfinite(res.theta)
    assert -4.5 <= res.theta <= 4.5


def test_8_eap_is_finite_for_all_wrong():
    """8. EAP é finito para all-wrong."""
    items = [ItemParameter(a=1.2, b=float(i) - 2.0, c=0.2) for i in range(5)]
    res = eap([0] * 5, items)

    assert np.isfinite(res.theta)
    assert -4.5 <= res.theta <= 4.5


def test_9_invalid_parameters_raise_value_errors():
    """9. erros de parâmetros inválidos."""
    # a <= 0
    with pytest.raises(ValueError, match="discriminação"):
        ItemParameter(a=0.0, b=0.0, c=0.2)
    with pytest.raises(ValueError, match="discriminação"):
        ItemParameter(a=-1.0, b=0.0, c=0.2)

    # c fora de [0, 1)
    with pytest.raises(ValueError, match="acerto ao acaso"):
        ItemParameter(a=1.0, b=0.0, c=-0.1)
    with pytest.raises(ValueError, match="acerto ao acaso"):
        ItemParameter(a=1.0, b=0.0, c=1.0)
    with pytest.raises(ValueError, match="acerto ao acaso"):
        ItemParameter(a=1.0, b=0.0, c=1.2)

    # D <= 0
    with pytest.raises(ValueError, match="Constante métrica 'D'"):
        ItemParameter(a=1.0, b=0.0, c=0.2, D=0.0)

    # Respostas com dimensões divergentes
    with pytest.raises(ValueError):
        eap([1, 0], [ItemParameter(a=1.0, b=0.0, c=0.2)])

    # Respostas inválidas (não 0 ou 1)
    with pytest.raises(ValueError):
        eap([2], [ItemParameter(a=1.0, b=0.0, c=0.2)])


def test_10_linear_transformation():
    """10. transformação linear."""
    thetas = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    true_alpha = 505.2
    true_beta = 98.4
    official_scores = true_alpha + true_beta * thetas

    scale = fit_linear_scale(thetas, official_scores)
    assert np.isclose(scale.alpha, true_alpha, atol=1e-5)
    assert np.isclose(scale.beta, true_beta, atol=1e-5)

    # Testa transformação direta e inversa
    val = scale.transform(1.5)
    assert np.isclose(scale.inverse(val), 1.5)

    # Teste de beta <= 0
    with pytest.raises(ValueError, match="beta"):
        fit_linear_scale(np.array([1.0, 2.0]), np.array([500.0, 400.0]))


def test_11_calibration_version_serialization():
    """11. serialização da CalibrationVersion."""
    cal = CalibrationVersion(
        calibration_id="enem-2025-mat-v1",
        exam_year=2025,
        application="regular",
        area="MT",
        scale_alpha=512.4,
        scale_beta=102.1,
        dataset_sha256="abc123hash",
        status="PUBLISHED",
        official_algorithm=False,
    )
    data = cal.to_dict()
    assert data["calibration_id"] == "enem-2025-mat-v1"
    assert data["official_algorithm"] is False

    reconstructed = CalibrationVersion.from_dict(data)
    assert reconstructed == cal

    # Garantia de recusa se official_algorithm for adulterado
    with pytest.raises(ValueError, match="official_algorithm"):
        CalibrationVersion(
            calibration_id="fake",
            exam_year=2025,
            application="regular",
            area="MT",
            official_algorithm=True,  # Proibido!
        )


def test_12_coverage_threshold_enforced():
    """12. coverage."""
    cal = CalibrationVersion(
        calibration_id="cal_test",
        exam_year=2025,
        application="regular",
        area="MT",
        minimum_coverage=0.8,
    )

    # 45 itens esperados, apenas 10 parametrizados => coverage 10/45 = 22.2% (< 80%)
    items_few = [ItemParameter(a=1.0, b=0.0, c=0.2)] * 10 + [None] * 35
    responses = [1] * 45

    with pytest.raises(ValueError, match="Cobertura de itens parametrizados"):
        score_pattern(responses, items_few, cal, expected_total_items=45)


def test_13_missing_parameters_not_silently_imputed():
    """13. parâmetros ausentes não são imputados silenciosamente."""
    cal = CalibrationVersion(
        calibration_id="cal_test",
        exam_year=2025,
        application="regular",
        area="MT",
        minimum_coverage=0.7,
    )

    # 35 itens com parâmetros, 10 itens sem parâmetros (None) => coverage = 35/45 = 77.7% (>= 70%)
    valid_p = ItemParameter(a=1.0, b=0.0, c=0.2)
    items = [valid_p] * 35 + [None] * 10
    responses = [1] * 45

    output = score_pattern(responses, items, cal, expected_total_items=45)

    assert output.parameterized_items == 35
    assert output.answered_items == 45
    assert output.coverage == pytest.approx(35 / 45, 0.01)
    # Verifica que warning explícito sobre questões desconsideradas foi gerado
    assert any("não possuem parâmetros válidos" in w for w in output.warnings)
    assert output.is_official is False
