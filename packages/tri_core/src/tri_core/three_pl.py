from __future__ import annotations

from typing import Sequence
import numpy as np
from numpy.typing import NDArray
from scipy.special import expit

from tri_core.models import ItemParameter, FloatArray

EPSILON = 1e-12


def probability_3pl(
    theta: FloatArray,
    item: ItemParameter,
) -> FloatArray:
    """Calcula a probabilidade de acerto P(X_i = 1 | theta) sob o modelo 3PL.

    P_i(theta) = c_i + (1.0 - c_i) * sigmoid(D * a_i * (theta - b_i))
    """
    theta_arr = np.asarray(theta, dtype=np.float64)
    z = item.D * item.a * (theta_arr - item.b)
    # expit é numericamente estável para sigmoid evitando overflow
    p = item.c + (1.0 - item.c) * expit(z)
    return np.clip(p, EPSILON, 1.0 - EPSILON)


def log_likelihood(
    responses: Sequence[int],
    items: Sequence[ItemParameter],
    theta: FloatArray,
) -> FloatArray:
    """Calcula log L(theta | u) = sum_i [ u_i * log(P_i) + (1 - u_i) * log(1 - P_i) ]

    Retorna array com log-verossimilhança para cada nó em theta.
    """
    if len(responses) != len(items):
        raise ValueError(
            f"Quantidade de respostas ({len(responses)}) difere da quantidade de itens ({len(items)})"
        )

    theta_arr = np.asarray(theta, dtype=np.float64)
    total_log_lik = np.zeros_like(theta_arr)

    for resp, item in zip(responses, items, strict=True):
        if resp not in (0, 1):
            raise ValueError(f"Resposta deve ser 0 ou 1, recebido {resp}")
        p = probability_3pl(theta_arr, item)
        if resp == 1:
            total_log_lik += np.log(p)
        else:
            total_log_lik += np.log1p(-p)

    return total_log_lik
