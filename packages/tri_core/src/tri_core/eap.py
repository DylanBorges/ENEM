from __future__ import annotations

from typing import Sequence
import numpy as np
from scipy.special import logsumexp

from tri_core.models import (
    ItemParameter,
    CalibrationVersion,
    EAPResult,
    ScoreEstimateOutput,
    FloatArray,
)
from tri_core.three_pl import log_likelihood


def _compute_posterior_quantiles(
    nodes: FloatArray,
    posterior: FloatArray,
    quantiles: Sequence[float],
) -> list[float]:
    """Calcula quantis da distribuição a posteriori acumulada por interpolação linear."""
    cdf = np.cumsum(posterior)
    # Garante normalização da CDF em [0, 1]
    cdf /= cdf[-1]
    results = []
    for q in quantiles:
        idx = np.searchsorted(cdf, q)
        if idx == 0:
            results.append(float(nodes[0]))
        elif idx >= len(nodes):
            results.append(float(nodes[-1]))
        else:
            # Interpolação linear entre nós adjacentes
            x0, x1 = nodes[idx - 1], nodes[idx]
            y0, y1 = cdf[idx - 1], cdf[idx]
            if y1 > y0:
                val = x0 + (q - y0) * (x1 - x0) / (y1 - y0)
            else:
                val = x0
            results.append(float(val))
    return results


def eap(
    responses: Sequence[int],
    params: Sequence[ItemParameter],
    *,
    nodes: FloatArray | None = None,
    prior_mean: float = 0.0,
    prior_sd: float = 1.0,
) -> EAPResult:
    """Estima a proficiência latente theta via Expected A Posteriori (EAP).

    Garante:
    - Estimativa finita e estável para padrões extremos (all-correct ou all-wrong).
    - Posterior normalizado integrando numericamente a 1.
    - Desvio padrão posterior e intervalo crível bayesiano de 95%.
    """
    if len(responses) != len(params):
        raise ValueError(
            f"Tamanho do vetor de respostas ({len(responses)}) deve coincidir com parâmetros ({len(params)})"
        )
    if len(responses) == 0:
        raise ValueError("Ao menos um item deve ser fornecido para estimativa EAP")

    for resp in responses:
        if resp not in (0, 1):
            raise ValueError(f"Cada resposta deve ser 0 ou 1, recebido {resp}")

    if nodes is None:
        nodes = np.linspace(-4.5, 4.5, 181, dtype=np.float64)
    else:
        nodes = np.asarray(nodes, dtype=np.float64)

    # Log da densidade a priori Normal(prior_mean, prior_sd)
    z_prior = (nodes - prior_mean) / prior_sd
    log_prior = -0.5 * (z_prior**2) - np.log(prior_sd * np.sqrt(2.0 * np.pi))

    # Log-verossimilhança somada sobre os itens
    log_lik = log_likelihood(responses, params, nodes)

    # Log posterior normalizada
    log_post = log_prior + log_lik
    log_post -= logsumexp(log_post)

    posterior = np.exp(log_post)
    # Garante soma exatamente 1.0 evitando drift de ponto flutuante
    posterior /= np.sum(posterior)

    theta_eap = float(np.sum(nodes * posterior))
    variance = float(np.sum(((nodes - theta_eap) ** 2) * posterior))
    posterior_sd = float(np.sqrt(max(variance, 0.0)))

    # Quantis 2.5%, 25%, 75%, 97.5%
    q_vals = _compute_posterior_quantiles(nodes, posterior, [0.025, 0.25, 0.75, 0.975])

    return EAPResult(
        theta=theta_eap,
        posterior_sd=posterior_sd,
        posterior=posterior,
        nodes=nodes,
        credible_interval_95=(q_vals[0], q_vals[3]),
        percentile_25=q_vals[1],
        percentile_75=q_vals[2],
    )


def score_pattern(
    responses: Sequence[int | None],
    items: Sequence[ItemParameter | None],
    calibration: CalibrationVersion,
    expected_total_items: int = 45,
) -> ScoreEstimateOutput:
    """Executa o scoring completo de uma área com tratamento rigoroso de itens sem parâmetros.

    Nunca inventa parâmetros faltantes.
    Calcula cobertura real e valida contra o limiar exigido pela calibração.
    """
    valid_responses: list[int] = []
    valid_params: list[ItemParameter] = []
    warnings: list[str] = [
        "Estimativa independente e não oficial do INEP. "
        "Não constitui reprodução exata da nota oficial."
    ]

    answered_count = 0
    raw_correct = 0

    for r, p in zip(responses, items):
        if r is not None:
            answered_count += 1
            if r == 1:
                raw_correct += 1
            if p is not None:
                valid_responses.append(r)
                valid_params.append(p)

    parameterized_count = len(valid_params)
    coverage = (
        float(parameterized_count / expected_total_items)
        if expected_total_items > 0
        else 0.0
    )

    if coverage < calibration.minimum_coverage:
        raise ValueError(
            f"Cobertura de itens parametrizados ({coverage:.1%}) está abaixo do mínimo "
            f"exigido ({calibration.minimum_coverage:.1%}) para a calibração '{calibration.calibration_id}'."
        )

    if parameterized_count < answered_count:
        unmodeled = answered_count - parameterized_count
        warnings.append(
            f"{unmodeled} questão(ões) respondida(s) não possuem parâmetros válidos nesta versão de calibração "
            f"e foram desconsideradas na estimativa latente."
        )

    # Configuração de grade e prior da calibração
    nodes = np.linspace(
        calibration.theta_min,
        calibration.theta_max,
        calibration.theta_points,
        dtype=np.float64,
    )
    eap_res = eap(
        valid_responses,
        valid_params,
        nodes=nodes,
        prior_mean=calibration.prior.mean,
        prior_sd=calibration.prior.sd,
    )

    # Transformação linear para escala estimada do ENEM: score = alpha + beta * theta
    estimated_score = calibration.scale_alpha + calibration.scale_beta * eap_res.theta
    lower_score = calibration.scale_alpha + calibration.scale_beta * eap_res.credible_interval_95[0]
    upper_score = calibration.scale_alpha + calibration.scale_beta * eap_res.credible_interval_95[1]

    return ScoreEstimateOutput(
        area=calibration.area,
        raw_correct=raw_correct,
        answered_items=answered_count,
        parameterized_items=parameterized_count,
        coverage=round(coverage, 4),
        theta_eap=round(eap_res.theta, 4),
        posterior_sd=round(eap_res.posterior_sd, 4),
        score_estimated=round(estimated_score, 1),
        credible_interval_95=(round(lower_score, 1), round(upper_score, 1)),
        calibration_id=calibration.calibration_id,
        model_version=calibration.code_version,
        is_official=False,
        warnings=warnings,
    )
