from __future__ import annotations

import json
import numpy as np
from typing import Any

from tri_core.models import ItemParameter, CalibrationVersion
from tri_core.calibration import MMLEMCalibration, CalibrationOptions
from tri_core.eap import eap
from tri_core.linking import fit_linear_scale
from tri_core.validation import evaluate_holdout


def run_full_calibration_pipeline(
    response_matrix: np.ndarray,
    official_scores: np.ndarray,
    exam_year: int = 2025,
    application: str = "regular",
    area: str = "MT",
    dataset_sha256: str = "synthetic_or_official_hash",
) -> tuple[CalibrationVersion, dict[str, Any]]:
    """Pipeline offline completo de calibração contra microdados.

    Divisão obrigatória anti-leakage:
    - 70% calibração de itens (MML/EM)
    - 15% linking de escala (ajuste de alpha/beta)
    - 15% holdout completamente intocado para validação final.
    """
    n_samples = len(response_matrix)
    if n_samples < 20:
        raise ValueError(f"Amostra insuficiente ({n_samples}) para calibração")

    indices = np.arange(n_samples)
    np.random.seed(42)
    np.random.shuffle(indices)

    idx_cal = int(0.70 * n_samples)
    idx_link = int(0.85 * n_samples)

    train_idx = indices[:idx_cal]
    link_idx = indices[idx_cal:idx_link]
    holdout_idx = indices[idx_link:]

    # 1. Calibração dos itens com MML / EM nos 70% de treino
    calibrator = MMLEMCalibration()
    opts = CalibrationOptions(max_iter=15, tol=1e-2, n_nodes=21)
    cal_result = calibrator.calibrate(response_matrix[train_idx], options=opts)
    calibrated_items = cal_result.items

    # 2. Linking nos 15% de ajuste (estimativa de theta e regressão de alpha/beta)
    link_responses = response_matrix[link_idx]
    link_official = official_scores[link_idx]

    thetas_link = []
    for resp in link_responses:
        eap_res = eap(list(resp), calibrated_items)
        thetas_link.append(eap_res.theta)

    linear_scale = fit_linear_scale(np.array(thetas_link), link_official)

    # 3. Validação final no HOLDOUT INTOCADO (15%)
    holdout_responses = response_matrix[holdout_idx]
    holdout_official = official_scores[holdout_idx]

    holdout_estimated = []
    holdout_raw = []
    for resp in holdout_responses:
        eap_res = eap(list(resp), calibrated_items)
        sc = linear_scale.transform(eap_res.theta)
        holdout_estimated.append(sc)
        holdout_raw.append(int(np.sum(resp)))

    val_metrics = evaluate_holdout(
        estimated_scores=np.array(holdout_estimated),
        official_scores=holdout_official,
        raw_corrects=holdout_raw,
    )

    cal_version = CalibrationVersion(
        calibration_id=f"enem-{exam_year}-{application}-{area.lower()}-v1",
        exam_year=exam_year,
        application=application,
        area=area,
        irt_model="3PL",
        estimator="EAP",
        D=1.0,
        scale_alpha=round(linear_scale.alpha, 2),
        scale_beta=round(linear_scale.beta, 2),
        minimum_coverage=0.7,
        validation_metrics=val_metrics.to_dict(),
        dataset_sha256=dataset_sha256,
        code_version="tri-core-0.1.0",
        # A publicação exige gate completo e auditoria explícita; este método
        # apenas produz uma candidata a calibração.
        status="DRAFT",
        official_algorithm=False,
    )

    return cal_version, {
        "items": [
            {"a": itm.a, "b": itm.b, "c": itm.c, "D": itm.D, "item_id": itm.item_id}
            for itm in calibrated_items
        ],
        "validation": val_metrics.to_dict(),
    }
