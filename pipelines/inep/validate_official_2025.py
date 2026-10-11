"""Valida EAP com parâmetros publicados pelo Inep em amostra separada.

Não publica calibração nem grava respostas individuais. Usa 1% dos registros
selecionados por hash determinístico: 70% reservados, 15% ligação de escala,
15% holdout. Os parâmetros a/b/c vêm da tabela oficial, sem estimação local.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import subprocess
import zipfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np
from scipy.special import expit, logsumexp

from pipelines.inep.audit_results_2025 import _seven_zip
from pipelines.inep.download import verify_sha256
from pipelines.inep.import_2025 import ARCHIVE, ROOT
from pipelines.inep.import_regular_2025 import OUTPUT as BOOKLETS_FILE
from tri_core.linking import fit_linear_scale
from tri_core.validation import evaluate_holdout

OUTPUT = ROOT / "data/processed/2025/validacao_notas_regulares.json"
AREAS = ("LC", "CH", "CN", "MT")


def split_bucket(sequence_id: str, year: int = 2025, sample_percent: int = 1) -> str | None:
    digest = hashlib.blake2b(sequence_id.encode("ascii"), digest_size=8,
                             person=f"enem{year}".encode("ascii")).digest()
    bucket = int.from_bytes(digest, "big") % 10000
    limit = sample_percent * 100
    if not 0 < limit <= 10000:
        raise ValueError("Percentual de amostragem fora do intervalo")
    if bucket >= limit:
        return None
    if bucket < limit * 0.70:
        return "reserved"
    return "link" if bucket < limit * 0.85 else "holdout"


def prepared_booklets(staged: dict[str, object]) -> dict[str, dict[str, object]]:
    result = {area: {} for area in AREAS}
    for booklet in staged["booklets"]:
        for area, data in booklet["areas"].items():
            rows = data["items"]
            code = str(data["booklet_code"])
            if area == "LC":
                by_position = {(row["position"], row["language"]): row for row in rows}
                all_keys = "".join(by_position[(position, "ingles")]["answer"] for position in range(1, 6))
                all_keys += "".join(by_position[(position, "espanhol")]["answer"] for position in range(1, 6))
                all_keys += "".join(by_position[(position, None)]["answer"] for position in range(6, 46))
                languages = {
                    language_code: [by_position[(position, language)] for position in range(1, 6)]
                    + [by_position[(position, None)] for position in range(6, 46)]
                    for language_code, language in (("0", "ingles"), ("1", "espanhol"))
                }
                result[area][code] = {"key50": all_keys, "languages": languages}
            else:
                ordered = sorted(rows, key=lambda row: row["position"])
                result[area][code] = {
                    "key45": "".join(row["answer"] or "X" for row in ordered),
                    "items": ordered,
                }
    return result


def eap_batch(correctness: np.ndarray, items: list[dict[str, object]]) -> np.ndarray:
    """Mesmo prior, grade e 3PL (D=1) de tri_core.eap, em lotes matriciais."""
    active = [item for item in items if item["parameters"] is not None]
    if correctness.ndim != 2 or correctness.shape[1] != len(active):
        raise ValueError("Respostas e parâmetros ativos não estão alinhados")
    nodes = np.linspace(-4.5, 4.5, 181, dtype=np.float64)
    a = np.array([item["parameters"]["a"] for item in active])
    b = np.array([item["parameters"]["b"] for item in active])
    c = np.array([item["parameters"]["c"] for item in active])
    p = c[None, :] + (1 - c[None, :]) * expit(a[None, :] * (nodes[:, None] - b[None, :]))
    p = np.clip(p, 1e-12, 1 - 1e-12)
    log_wrong = np.log1p(-p)
    log_ratio = np.log(p) - log_wrong
    log_prior = -0.5 * nodes**2 - math.log(math.sqrt(2 * math.pi))
    log_posterior = correctness @ log_ratio.T + log_wrong.sum(axis=1)[None, :] + log_prior[None, :]
    log_posterior -= logsumexp(log_posterior, axis=1, keepdims=True)
    return np.exp(log_posterior) @ nodes


@contextmanager
def _results_stream(archive: Path, year: int):
    member = f"microdados_enem_{year}/DADOS/RESULTADOS_{year}.csv"
    if year == 2024:
        with zipfile.ZipFile(archive) as source:
            with source.open(member) as raw:
                with io.TextIOWrapper(raw, encoding="latin-1", newline="") as stream:
                    yield stream
        return
    process = subprocess.Popen([_seven_zip(), "x", "-so", str(archive), member],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert process.stdout is not None
        with io.TextIOWrapper(process.stdout, encoding="latin-1", newline="") as stream:
            yield stream
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        if process.wait() != 0:
            raise RuntimeError(f"7-Zip falhou: {stderr[-500:]}")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def collect_sample(archive: Path, mappings: dict[str, dict[str, object]],
                   year: int = 2025, sample_percent: int = 1) -> tuple[dict, dict]:
    data = {area: {split: {"responses": [], "scores": [], "raw_correct": [], "codes": []}
                   for split in ("link", "holdout")} for area in AREAS}
    audit = {area: {"reserved": 0, "link": 0, "holdout": 0,
                    "all_blank_zero": 0, "invalid": 0} for area in AREAS}
    with _results_stream(archive, year) as stream:
            reader = csv.DictReader(stream, delimiter=";")
            required = {"NU_SEQUENCIAL", "TP_LINGUA"} | {
                f"{prefix}_{area}" for prefix in
                ("CO_PROVA", "TP_PRESENCA", "TX_RESPOSTAS", "TX_GABARITO", "NU_NOTA")
                for area in AREAS
            }
            if not required.issubset(reader.fieldnames or []):
                raise ValueError("Colunas de resultados necessárias ausentes")
            for row in reader:
                split = split_bucket(row["NU_SEQUENCIAL"], year, sample_percent)
                if split is None:
                    continue
                for area in AREAS:
                    code = row[f"CO_PROVA_{area}"]
                    if row[f"TP_PRESENCA_{area}"] != "1" or code not in mappings[area]:
                        continue
                    audit[area][split] += 1
                    if split == "reserved":
                        continue
                    mapping = mappings[area][code]
                    language = row["TP_LINGUA"]
                    if area == "LC":
                        if language not in mapping["languages"]:
                            audit[area]["invalid"] += 1
                            continue
                        items = mapping["languages"][language]
                        full_key = mapping["key50"]
                    else:
                        items = mapping["items"]
                        full_key = mapping["key45"]
                    response = row[f"TX_RESPOSTAS_{area}"]
                    official_key = row[f"TX_GABARITO_{area}"]
                    try:
                        score = float(row[f"NU_NOTA_{area}"])
                    except ValueError:
                        audit[area]["invalid"] += 1
                        continue
                    if (len(response) != 45 or official_key != full_key
                            or not math.isfinite(score)):
                        audit[area]["invalid"] += 1
                        continue
                    if len(response) == 45 and set(response) <= {".", "*"} and score == 0:
                        audit[area]["all_blank_zero"] += 1
                        continue
                    if score <= 0:
                        audit[area]["invalid"] += 1
                        continue
                    active = [item for item in items if item["parameters"] is not None]
                    vector = [int(response[item["position"] - (1 if area == "LC" else
                                46 if area == "CH" else 91 if area == "CN" else 136)] == item["answer"])
                              for item in active]
                    target = data[area][split]
                    target["responses"].append(vector)
                    target["scores"].append(score)
                    target["raw_correct"].append(sum(vector))
                    target["codes"].append(code + (language if area == "LC" else ""))
    return data, audit


def run(archive: Path = ARCHIVE, booklets_file: Path = BOOKLETS_FILE,
        output: Path = OUTPUT, year: int = 2025, sample_percent: int = 1) -> dict[str, object]:
    staged = json.loads(booklets_file.read_text(encoding="utf-8"))
    if staged["year"] != year:
        raise ValueError("Ano do mapeamento não corresponde ao ano solicitado")
    if not verify_sha256(str(archive), staged["source_microdados_sha256"]):
        raise ValueError("SHA-256 dos microdados diverge do mapeamento")
    mappings = prepared_booklets(staged)
    data, audit = collect_sample(archive, mappings, year, sample_percent)
    validations = {}
    for area in AREAS:
        # Calcula theta por código de caderno e, em Linguagens, por idioma.
        theta = {}
        for split in ("link", "holdout"):
            sample = data[area][split]
            if len(sample["responses"]) < 100:
                raise ValueError(f"Amostra insuficiente para {area}/{split}")
            estimated = np.empty(len(sample["responses"]), dtype=np.float64)
            groups = {}
            for index, code in enumerate(sample["codes"]):
                groups.setdefault(code, []).append(index)
            for code, indices in groups.items():
                language = code[-1] if area == "LC" else None
                booklet_code = code[:-1] if area == "LC" else code
                mapping = mappings[area][booklet_code]
                items = mapping["languages"][language] if area == "LC" else mapping["items"]
                matrix = np.asarray([sample["responses"][index] for index in indices], dtype=np.float64)
                estimated[indices] = eap_batch(matrix, items)
            theta[split] = estimated
        link = data[area]["link"]
        holdout = data[area]["holdout"]
        scale = fit_linear_scale(theta["link"], np.asarray(link["scores"]))
        scores = scale.transform(theta["holdout"])
        metrics = evaluate_holdout(scores, np.asarray(holdout["scores"]), holdout["raw_correct"])
        absolute_errors = np.abs(scores - np.asarray(holdout["scores"]))
        diagnostics = {
            "official_zero_scores": int(np.sum(np.asarray(holdout["scores"]) == 0)),
            "errors_over_35": int(np.sum(absolute_errors > 35)),
            "errors_over_100": int(np.sum(absolute_errors > 100)),
            "p99_absolute_error": round(float(np.percentile(absolute_errors, 99)), 2),
            "max_absolute_error": round(float(np.max(absolute_errors)), 2),
        }
        validations[area] = {
            "link_count": len(link["scores"]), "holdout_count": len(holdout["scores"]),
            "scale_alpha": round(scale.alpha, 6), "scale_beta": round(scale.beta, 6),
            "metrics": metrics.to_dict(),
            "diagnostics": diagnostics,
            "release_gate_passed": metrics.mae <= 35 and metrics.correlation >= 0.85,
        }
    result = {
        "year": year, "application": "regular", "official": False,
        "disclaimer": "Estimador independente, não reproduz o algoritmo oficial do Inep.",
        "source_microdados_sha256": staged["source_microdados_sha256"],
        "sampling": f"Blake2b de NU_SEQUENCIAL; {sample_percent}% selecionado; 70% reservado, 15% link, 15% holdout",
        "irt": "3PL, parâmetros publicados pelo Inep, D=1, EAP N(0,1), 181 nós [-4.5,4.5]",
        "audit": audit, "areas": validations,
        "published_to_api": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({area: {"link": data["link_count"], "holdout": data["holdout_count"],
                             "mae": data["metrics"]["mae"], "correlation": data["metrics"]["correlation"],
                             "release_gate_passed": data["release_gate_passed"]}
                      for area, data in result["areas"].items()}, ensure_ascii=False))
