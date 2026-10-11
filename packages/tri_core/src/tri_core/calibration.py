from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence, Any
import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize
from scipy.special import logsumexp

from tri_core.models import ItemParameter, PriorConfig, FloatArray
from tri_core.three_pl import probability_3pl

EPSILON = 1e-12


@dataclass(frozen=True)
class CalibrationOptions:
    max_iter: int = 50
    tol: float = 1e-3
    n_nodes: int = 31
    theta_min: float = -4.0
    theta_max: float = 4.0
    D: float = 1.0
    estimate_c: bool = True
    c_fixed: float = 0.2


@dataclass(frozen=True)
class ItemDiagnostic:
    item_index: int
    converged: bool
    iterations: int
    flag_extreme_a: bool
    flag_extreme_b: bool
    flag_boundary_c: bool
    message: str = "OK"


@dataclass(frozen=True)
class CalibrationResult:
    items: list[ItemParameter]
    converged: bool
    iterations: int
    log_marginal_likelihood: float
    diagnostics: list[ItemDiagnostic]
    metadata: dict[str, Any] = field(default_factory=dict)


class CalibrationBackend(Protocol):
    """Protocolo formal para algoritmos de calibração de itens TRI."""

    def calibrate(
        self,
        response_matrix: NDArray[np.int32],
        initial_items: Sequence[ItemParameter] | None = None,
        options: CalibrationOptions | None = None,
    ) -> CalibrationResult:
        ...


class MMLEMCalibration:
    """Calibração de Máxima Verossimilhança Marginal com algoritmo EM (Bock & Aitkin, 1981).

    Executa calibração independente para modelo 3PL integrando sobre a distribuição latente.
    """

    def __init__(self, prior: PriorConfig | None = None) -> None:
        self.prior = prior or PriorConfig()

    def calibrate(
        self,
        response_matrix: NDArray[np.int32],
        initial_items: Sequence[ItemParameter] | None = None,
        options: CalibrationOptions | None = None,
    ) -> CalibrationResult:
        opts = options or CalibrationOptions()
        U = np.asarray(response_matrix, dtype=np.float64)
        n_examinees, n_items = U.shape

        if n_examinees < 10 or n_items < 2:
            raise ValueError(
                f"Amostra insuficiente para calibração: {n_examinees} participantes, {n_items} itens"
            )

        # 1. Nós de quadratura e prior
        nodes = np.linspace(opts.theta_min, opts.theta_max, opts.n_nodes, dtype=np.float64)
        z_prior = (nodes - self.prior.mean) / self.prior.sd
        log_prior_density = -0.5 * (z_prior**2) - np.log(self.prior.sd * np.sqrt(2.0 * np.pi))
        prior_weights = np.exp(log_prior_density - logsumexp(log_prior_density))

        # 2. Inicialização dos parâmetros dos itens
        current_items: list[ItemParameter] = []
        if initial_items and len(initial_items) == n_items:
            current_items = list(initial_items)
        else:
            p_values = np.mean(U, axis=0)
            for i, p_val in enumerate(p_values):
                # Inicialização heurística razoável para 3PL
                p_safe = np.clip(p_val, 0.05, 0.95)
                # Dificuldade inversa da proporção de acertos
                b_init = float(-np.log(p_safe / (1.0 - p_safe)))
                c_init = opts.c_fixed if not opts.estimate_c else 0.2
                current_items.append(
                    ItemParameter(a=1.0, b=b_init, c=c_init, D=opts.D, item_id=f"item_{i+1}")
                )

        converged = False
        iteration = 0
        last_log_lik = -np.inf

        for it in range(1, opts.max_iter + 1):
            iteration = it

            # --- E-STEP ---
            # Matriz de log P(X_i = 1 | theta_k) para todos itens e nós: shape (n_items, n_nodes)
            log_P = np.zeros((n_items, opts.n_nodes), dtype=np.float64)
            log_Q = np.zeros((n_items, opts.n_nodes), dtype=np.float64)
            for i, itm in enumerate(current_items):
                p_nodes = probability_3pl(nodes, itm)
                log_P[i, :] = np.log(p_nodes)
                log_Q[i, :] = np.log1p(-p_nodes)

            # Para cada examinando, log L(theta_k | U_p) = U_p @ log_P + (1 - U_p) @ log_Q
            # Shape: (n_examinees, n_nodes)
            log_lik_matrix = U @ log_P + (1.0 - U) @ log_Q

            # log P(theta_k | U_p) = log L + log_prior - logsumexp
            log_post = log_lik_matrix + np.log(prior_weights + EPSILON)
            norm_factor = logsumexp(log_post, axis=1, keepdims=True)
            post_weights = np.exp(log_post - norm_factor)  # (n_examinees, n_nodes)

            # Verossimilhança marginal total desta iteração
            current_log_lik = float(np.sum(norm_factor))

            # Frequências esperadas nos nós:
            # n_k = sum_p post_weights[p, k]
            n_k = np.sum(post_weights, axis=0)  # (n_nodes,)
            # r_{i, k} = sum_p post_weights[p, k] * U[p, i]
            r_ik = post_weights.T @ U  # (n_nodes, n_items)

            # --- M-STEP ---
            max_delta = 0.0
            new_items: list[ItemParameter] = []

            for i in range(n_items):
                r_k = r_ik[:, i]
                itm = current_items[i]

                def neg_expected_log_lik(params: Sequence[float]) -> float:
                    if opts.estimate_c:
                        a_val, b_val, c_val = params
                    else:
                        a_val, b_val = params
                        c_val = opts.c_fixed

                    test_itm = ItemParameter(a=a_val, b=b_val, c=c_val, D=opts.D)
                    p_val = probability_3pl(nodes, test_itm)
                    ll = np.sum(r_k * np.log(p_val) + (n_k - r_k) * np.log1p(-p_val))
                    return -float(ll)

                if opts.estimate_c:
                    x0 = [itm.a, itm.b, itm.c]
                    bounds = [(0.2, 3.5), (-4.0, 4.0), (0.0, 0.40)]
                else:
                    x0 = [itm.a, itm.b]
                    bounds = [(0.2, 3.5), (-4.0, 4.0)]

                opt_res = minimize(
                    neg_expected_log_lik,
                    x0=x0,
                    method="L-BFGS-B",
                    bounds=bounds,
                    options={"maxiter": 20},
                )

                if opts.estimate_c:
                    new_a, new_b, new_c = opt_res.x
                else:
                    new_a, new_b = opt_res.x
                    new_c = opts.c_fixed

                delta = max(abs(new_a - itm.a), abs(new_b - itm.b), abs(new_c - itm.c))
                if delta > max_delta:
                    max_delta = delta

                new_items.append(
                    ItemParameter(
                        a=float(new_a),
                        b=float(new_b),
                        c=float(new_c),
                        D=opts.D,
                        item_id=itm.item_id,
                    )
                )

            current_items = new_items
            last_log_lik = current_log_lik

            if max_delta < opts.tol:
                converged = True
                break

        # 3. Diagnósticos por item
        diagnostics: list[ItemDiagnostic] = []
        for i, itm in enumerate(current_items):
            ext_a = itm.a <= 0.25 or itm.a >= 3.4
            ext_b = itm.b <= -3.8 or itm.b >= 3.8
            bnd_c = itm.c >= 0.38
            flags = []
            if ext_a:
                flags.append("discriminação_extrema")
            if ext_b:
                flags.append("dificuldade_extrema")
            if bnd_c:
                flags.append("limite_acaso")

            msg = "OK" if not flags else "; ".join(flags)
            diagnostics.append(
                ItemDiagnostic(
                    item_index=i,
                    converged=converged,
                    iterations=iteration,
                    flag_extreme_a=ext_a,
                    flag_extreme_b=ext_b,
                    flag_boundary_c=bnd_c,
                    message=msg,
                )
            )

        return CalibrationResult(
            items=current_items,
            converged=converged,
            iterations=iteration,
            log_marginal_likelihood=last_log_lik,
            diagnostics=diagnostics,
            metadata={
                "n_examinees": n_examinees,
                "n_items": n_items,
                "options": {
                    "max_iter": opts.max_iter,
                    "tol": opts.tol,
                    "n_nodes": opts.n_nodes,
                    "D": opts.D,
                },
            },
        )
