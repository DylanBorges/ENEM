from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Sequence
import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ItemParameter:
    """Parâmetros de um item no modelo logístico 3PL.

    P_i(theta) = c_i + (1 - c_i) / (1 + exp[-D * a_i * (theta - b_i)])

    Restrições obrigatórias:
    - a > 0: discriminação
    - 0 <= c < 1: assíntota inferior (acerto ao acaso)
    - D > 0: constante de escala logística (D=1.0 ou D=1.7)
    """

    a: float
    b: float
    c: float
    D: float = 1.0
    item_id: str = ""

    def __post_init__(self) -> None:
        if not np.isfinite(self.a) or self.a <= 0:
            raise ValueError(f"Parâmetro 'a' (discriminação) deve ser finito e > 0, recebido {self.a}")
        if not np.isfinite(self.b):
            raise ValueError(f"Parâmetro 'b' (dificuldade) deve ser finito, recebido {self.b}")
        if not np.isfinite(self.c) or not (0.0 <= self.c < 1.0):
            raise ValueError(f"Parâmetro 'c' (acerto ao acaso) deve satisfazer 0 <= c < 1, recebido {self.c}")
        if not np.isfinite(self.D) or self.D <= 0:
            raise ValueError(f"Constante métrica 'D' deve ser > 0, recebido {self.D}")


@dataclass(frozen=True)
class PriorConfig:
    """Configuração da distribuição a priori g(theta)."""

    distribution: str = "normal"
    mean: float = 0.0
    sd: float = 1.0

    def __post_init__(self) -> None:
        if self.distribution != "normal":
            raise ValueError(f"Distribuição a priori não suportada: {self.distribution}")
        if self.sd <= 0:
            raise ValueError(f"Desvio padrão a priori deve ser > 0, recebido {self.sd}")


@dataclass(frozen=True)
class EAPResult:
    """Resultado da estimativa Expected A Posteriori."""

    theta: float
    posterior_sd: float
    posterior: FloatArray
    nodes: FloatArray
    credible_interval_95: tuple[float, float]
    percentile_25: float
    percentile_75: float


@dataclass(frozen=True)
class CalibrationVersion:
    """Metadados e parâmetros imutáveis de uma versão de calibração."""

    calibration_id: str
    exam_year: int
    application: str  # ex: "regular", "reaplicacao"
    area: str  # ex: "CH", "CN", "LC", "MT"
    irt_model: str = "3PL"
    estimator: str = "EAP"
    D: float = 1.0
    prior: PriorConfig = field(default_factory=PriorConfig)
    theta_min: float = -4.5
    theta_max: float = 4.5
    theta_points: int = 181
    scale_alpha: float = 500.0
    scale_beta: float = 100.0
    minimum_coverage: float = 0.7
    validation_metrics: dict[str, Any] = field(default_factory=dict)
    dataset_sha256: str = ""
    code_version: str = "tri-core-0.1.0"
    status: str = "PUBLISHED"  # "DRAFT", "PUBLISHED", "DEPRECATED"
    official_algorithm: bool = False

    def __post_init__(self) -> None:
        if self.scale_beta <= 0:
            raise ValueError("scale_beta da transformação linear deve ser estritamente positiva")
        if not (0.0 < self.minimum_coverage <= 1.0):
            raise ValueError("minimum_coverage deve estar no intervalo (0, 1]")
        if self.official_algorithm is not False:
            raise ValueError("official_algorithm deve ser estritamente False (estimador não oficial)")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationVersion:
        data = data.copy()
        if "prior" in data and isinstance(data["prior"], dict):
            data["prior"] = PriorConfig(**data["prior"])
        return cls(**data)


@dataclass(frozen=True)
class ScoreEstimateOutput:
    """Saída padronizada de pontuação de um estudante para uma área."""

    area: str
    raw_correct: int
    answered_items: int
    parameterized_items: int
    coverage: float
    theta_eap: float
    posterior_sd: float
    score_estimated: float
    credible_interval_95: tuple[float, float]
    calibration_id: str
    model_version: str
    is_official: bool = False
    warnings: list[str] = field(default_factory=list)
