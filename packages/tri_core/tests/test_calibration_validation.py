import numpy as np
import pytest

from tri_core.models import ItemParameter
from tri_core.calibration import MMLEMCalibration, CalibrationOptions
from tri_core.validation import evaluate_holdout


def test_mmlem_calibration_recovers_synthetic_parameters():
    """Valida o funcionamento do estimador Marginal Maximum Likelihood / EM em dados sintéticos."""
    np.random.seed(42)
    n_examinees = 300
    n_items = 6

    # Gera habilidades latentes da população N(0, 1)
    true_theta = np.random.normal(0.0, 1.0, size=n_examinees)

    # Parâmetros verdadeiros
    true_items = [
        ItemParameter(a=1.2, b=-1.0, c=0.2),
        ItemParameter(a=1.5, b=-0.5, c=0.2),
        ItemParameter(a=1.0, b=0.0, c=0.2),
        ItemParameter(a=1.4, b=0.5, c=0.2),
        ItemParameter(a=1.1, b=1.0, c=0.2),
        ItemParameter(a=1.3, b=1.5, c=0.2),
    ]

    # Gera matriz de respostas simulada
    responses = np.zeros((n_examinees, n_items), dtype=np.int32)
    for j, itm in enumerate(true_items):
        z = itm.a * (true_theta - itm.b)
        prob = itm.c + (1.0 - itm.c) / (1.0 + np.exp(-z))
        responses[:, j] = (np.random.uniform(0, 1, size=n_examinees) < prob).astype(np.int32)

    # Executa calibração com poucas iterações para teste unitário ágil
    calibrator = MMLEMCalibration()
    opts = CalibrationOptions(max_iter=6, tol=1e-2, n_nodes=21, estimate_c=False, c_fixed=0.2)
    result = calibrator.calibrate(responses, options=opts)

    assert len(result.items) == n_items
    assert len(result.diagnostics) == n_items
    # Dificuldades calibradas devem preservar a ordenação geral dos itens
    calibrated_b = [itm.b for itm in result.items]
    assert calibrated_b[0] < calibrated_b[-1]


def test_evaluate_holdout_metrics():
    """Valida cálculo de métricas de validação psicométrica no holdout."""
    official = np.array([400.0, 500.0, 600.0, 700.0, 800.0])
    # Estimativa com pequeno erro
    estimated = np.array([405.0, 495.0, 610.0, 690.0, 805.0])
    raws = [10, 20, 30, 38, 44]

    metrics = evaluate_holdout(estimated, official, raws)

    assert metrics.n_samples == 5
    assert metrics.mae == pytest.approx(7.0, 0.1)
    assert metrics.correlation > 0.99
    assert metrics.r_squared > 0.98
    assert "D1" in metrics.error_by_decile
    assert "10" in metrics.error_by_raw_score
