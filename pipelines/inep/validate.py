from typing import Any
from tri_core.models import CalibrationVersion


def check_release_gate(
    calibration: CalibrationVersion,
    max_acceptable_mae: float = 35.0,
    min_acceptable_correlation: float = 0.85,
) -> dict[str, Any]:
    """Release Gate Psicométrico:

    Impede a publicação de qualquer calibração que não satisfaça os limites
    de erro e correlação comprovados em holdout intocado.
    """
    metrics = calibration.validation_metrics
    mae = float(metrics.get("mae", 999.0))
    corr = float(metrics.get("correlation", 0.0))

    passed_mae = mae <= max_acceptable_mae
    passed_corr = corr >= min_acceptable_correlation
    passed = passed_mae and passed_corr

    return {
        "calibration_id": calibration.calibration_id,
        "passed": passed,
        "status": "APPROVED_FOR_PUBLICATION" if passed else "REJECTED",
        "criteria": {
            "mae": {"value": mae, "threshold": max_acceptable_mae, "passed": passed_mae},
            "correlation": {"value": corr, "threshold": min_acceptable_correlation, "passed": passed_corr},
        },
    }
