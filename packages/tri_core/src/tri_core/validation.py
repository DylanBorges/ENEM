from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import numpy as np

from tri_core.models import FloatArray


@dataclass(frozen=True)
class ValidationMetrics:
    mae: float
    rmse: float
    bias: float
    median_absolute_error: float
    p90_absolute_error: float
    p95_absolute_error: float
    correlation: float
    r_squared: float
    n_samples: int
    error_by_decile: dict[str, float]
    error_by_raw_score: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_holdout(
    estimated_scores: FloatArray,
    official_scores: FloatArray,
    raw_corrects: list[int] | FloatArray | None = None,
) -> ValidationMetrics:
    """Calcula métricas rigorosas de validação psicométrica no conjunto de holdout intocado.

    Gera diagnóstico por decil e por número de acertos brutos para identificar desvios
    nas caudas ou distorções sistemáticas.
    """
    est = np.asarray(estimated_scores, dtype=np.float64)
    off = np.asarray(official_scores, dtype=np.float64)

    if est.shape != off.shape:
        raise ValueError(f"Dimensões incompatíveis: est={est.shape}, off={off.shape}")
    if len(est) == 0:
        raise ValueError("Conjunto de validação não pode ser vazio")

    errors = est - off
    abs_errors = np.abs(errors)

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors**2)))
    bias = float(np.mean(errors))
    median_abs = float(np.median(abs_errors))
    p90_abs = float(np.percentile(abs_errors, 90))
    p95_abs = float(np.percentile(abs_errors, 95))

    # Correlação de Pearson e R^2
    if np.std(est) > 1e-9 and np.std(off) > 1e-9:
        corr = float(np.corrcoef(est, off)[0, 1])
        ss_res = np.sum(errors**2)
        ss_tot = np.sum((off - np.mean(off)) ** 2)
        r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
    else:
        corr = 0.0
        r2 = 0.0

    # Erro médio absoluto por decil da nota oficial
    error_by_decile: dict[str, float] = {}
    quantiles = np.percentile(off, np.linspace(0, 100, 11))
    for i in range(10):
        low, high = quantiles[i], quantiles[i + 1]
        mask = (off >= low) & (off <= high) if i == 9 else (off >= low) & (off < high)
        if np.any(mask):
            error_by_decile[f"D{i+1}"] = round(float(np.mean(abs_errors[mask])), 2)
        else:
            error_by_decile[f"D{i+1}"] = 0.0

    # Erro médio absoluto por quantidade de acertos brutos (quando fornecido)
    error_by_raw_score: dict[str, float] = {}
    if raw_corrects is not None:
        raw_arr = np.asarray(raw_corrects, dtype=np.int32)
        if raw_arr.shape == est.shape:
            unique_raws = np.unique(raw_arr)
            for r in unique_raws:
                mask = raw_arr == r
                error_by_raw_score[str(int(r))] = round(float(np.mean(abs_errors[mask])), 2)

    return ValidationMetrics(
        mae=round(mae, 2),
        rmse=round(rmse, 2),
        bias=round(bias, 2),
        median_absolute_error=round(median_abs, 2),
        p90_absolute_error=round(p90_abs, 2),
        p95_absolute_error=round(p95_abs, 2),
        correlation=round(corr, 4),
        r_squared=round(r2, 4),
        n_samples=len(est),
        error_by_decile=error_by_decile,
        error_by_raw_score=error_by_raw_score,
    )
