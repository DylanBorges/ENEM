"""tri_core: Núcleo psicométrico puro de Teoria de Resposta ao Item (TRI) para o ENEM.

Biblioteca matemática determinística, auditável e sem dependências de framework web ou banco.
"""

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
from tri_core.validation import evaluate_holdout, ValidationMetrics
from tri_core.calibration import MMLEMCalibration, CalibrationResult, CalibrationBackend

__all__ = [
    "ItemParameter",
    "PriorConfig",
    "CalibrationVersion",
    "EAPResult",
    "ScoreEstimateOutput",
    "probability_3pl",
    "log_likelihood",
    "eap",
    "score_pattern",
    "LinearScale",
    "fit_linear_scale",
    "evaluate_holdout",
    "ValidationMetrics",
    "MMLEMCalibration",
    "CalibrationResult",
    "CalibrationBackend",
]

__version__ = "0.1.0"
