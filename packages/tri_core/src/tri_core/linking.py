from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from tri_core.models import FloatArray


@dataclass(frozen=True)
class LinearScale:
    """Transformação linear da escala latente theta para a escala estimada do ENEM:

    score = alpha + beta * theta
    """

    alpha: float
    beta: float

    def __post_init__(self) -> None:
        if not np.isfinite(self.alpha):
            raise ValueError(f"alpha deve ser finito, recebido {self.alpha}")
        if not np.isfinite(self.beta) or self.beta <= 0:
            raise ValueError(f"beta deve ser finito e estritamente positivo, recebido {self.beta}")

    def transform(self, theta: float | FloatArray) -> float | FloatArray:
        """Converte proficiência theta em nota estimada."""
        return self.alpha + self.beta * theta

    def inverse(self, score: float | FloatArray) -> float | FloatArray:
        """Converte nota estimada de volta para a proficiência theta."""
        return (score - self.alpha) / self.beta


def fit_linear_scale(
    theta: FloatArray,
    official_score: FloatArray,
) -> LinearScale:
    """Ajusta os coeficientes alpha e beta via Mínimos Quadrados Ordinários (OLS):

    S^{oficial} = alpha + beta * theta + erro

    ATENÇÃO:
    - Deve ser executado SOMENTE no conjunto de treino/linking, NUNCA no holdout.
    - beta DEVE ser positiva (maior proficiência implica maior nota).
    """
    theta_arr = np.asarray(theta, dtype=np.float64)
    official_arr = np.asarray(official_score, dtype=np.float64)

    if theta_arr.ndim != 1 or official_arr.ndim != 1:
        raise ValueError("theta e official_score devem ser vetores unidimensionais")
    if theta_arr.shape[0] != official_arr.shape[0]:
        raise ValueError(
            f"Tamanho de theta ({theta_arr.shape[0]}) difere de official_score ({official_arr.shape[0]})"
        )
    if len(theta_arr) < 2:
        raise ValueError("São necessários pelo menos 2 pontos para estimar alpha e beta")

    # Matriz de delineamento [1, theta]
    X = np.column_stack([np.ones_like(theta_arr), theta_arr])

    coef, _, _, _ = np.linalg.lstsq(X, official_arr, rcond=None)
    alpha = float(coef[0])
    beta = float(coef[1])

    if beta <= 0:
        raise ValueError(
            f"Ajuste linear inválido: beta resultante ({beta:.4f}) é não-positivo. "
            "Verifique se o padrão de respostas e as notas oficiais estão alinhados."
        )

    return LinearScale(alpha=alpha, beta=beta)
