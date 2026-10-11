"""Audita itens do segundo dia, caderno amarelo, do ENEM 2025.

Executar: python -m pipelines.inep.import_2025
O resultado fica em data/processed e não publica calibração na API.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

import yaml
from pypdf import PdfReader

from pipelines.inep.download import verify_sha256


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "pipelines/inep/manifests/2025.yaml"
ARCHIVE = ROOT / "data/raw/2025/microdados_enem_2025.zip"
OFFICIAL_KEY = ROOT / "data/raw/2025/2025_GB_impresso_D2_CD5.pdf"
OUTPUT = ROOT / "data/processed/2025/itens_d2_caderno5_amarelo.json"
AREA_RANGES = {"CN": range(91, 136), "MT": range(136, 181)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_official_key(path: Path) -> dict[int, str]:
    if len(PdfReader(str(path)).pages) != 1:
        raise ValueError("Gabarito PDF inesperado: número de páginas")
    text = PdfReader(str(path)).pages[0].extract_text()
    pairs = re.findall(r"(?m)^(\d{2,3})\s+([A-E]|Anulado)$", text)
    key = {int(position): "X" if answer == "Anulado" else answer for position, answer in pairs}
    expected = set(AREA_RANGES["CN"]) | set(AREA_RANGES["MT"])
    if len(pairs) != 90 or set(key) != expected:
        raise ValueError("Gabarito PDF incompleto ou com posições duplicadas")
    return key


def read_items(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith("/DADOS/ITENS_PROVA_2025.csv")]
        if len(members) != 1:
            raise ValueError("Tabela oficial de itens não encontrada de forma única")
        with archive.open(members[0]) as raw:
            with io.TextIOWrapper(raw, encoding="latin-1", newline="") as stream:
                return list(csv.DictReader(stream, delimiter=";"))


def select_booklets(rows: list[dict[str, str]], key: dict[int, str]) -> dict[str, list[dict[str, str]]]:
    selected = {}
    for area, positions in AREA_RANGES.items():
        candidates = defaultdict(list)
        for row in rows:
            if row["SG_AREA"] == area and row["TX_COR"].upper() == "AMARELA":
                candidates[row["CO_PROVA"]].append(row)
        matches = []
        for code, candidate in candidates.items():
            by_position = {int(row["CO_POSICAO"]): row for row in candidate}
            if len(candidate) == len(positions) and set(by_position) == set(positions) and all(
                by_position[position]["TX_GABARITO"] == key[position] for position in positions
            ):
                matches.append((code, [by_position[position] for position in positions]))
        if len(matches) != 1:
            raise ValueError(f"Esperado um caderno amarelo para {area}; encontrados {len(matches)}")
        selected[area] = matches[0][1]
    return selected


def normalize_item(row: dict[str, str]) -> dict[str, object]:
    annulled = row["TX_GABARITO"] == "X"
    excluded = row["IN_ITEM_ABAN"] == "1"
    if annulled and not excluded:
        raise ValueError("Questão anulada sem indicação de exclusão psicométrica")
    param_fields = (row["NU_PARAM_A"], row["NU_PARAM_B"], row["NU_PARAM_C"])
    if excluded:
        if any(param_fields):
            raise ValueError("Questão excluída possui parâmetros psicométricos")
        parameters = None
    else:
        if not all(param_fields):
            raise ValueError("Questão ativa sem parâmetros psicométricos")
        a, b, c = map(float, param_fields)
        if a <= 0 or not 0 <= c < 1:
            raise ValueError("Parâmetros psicométricos fora do domínio esperado")
        parameters = {"a": a, "b": b, "c": c}
    return {
        "position": int(row["CO_POSICAO"]),
        "area": row["SG_AREA"],
        "language": {"0": "ingles", "1": "espanhol"}.get(row.get("TP_LINGUA", "")),
        "booklet_code": int(row["CO_PROVA"]),
        "inep_item_id": int(row["CO_ITEM"]),
        "answer": None if annulled else row["TX_GABARITO"],
        "annulled_in_official_key": annulled,
        "excluded_from_psychometrics": excluded,
        "exclusion_reason": row["TX_MOTIVO_ABAN"] or None,
        "skill_code": int(row["CO_HABILIDADE"]),
        "parameters": parameters,
    }


def run(archive: Path = ARCHIVE, pdf: Path = OFFICIAL_KEY, output: Path = OUTPUT) -> dict[str, object]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if not verify_sha256(str(archive), manifest["sha256"]):
        raise ValueError("SHA-256 do pacote de microdados diverge do manifesto")
    pdf_hash = sha256(pdf)
    if pdf_hash != manifest["official_key_sha256"]:
        raise ValueError("SHA-256 do gabarito oficial diverge do manifesto")
    selected = select_booklets(read_items(archive), read_official_key(pdf))
    items = [normalize_item(row) for area in ("CN", "MT") for row in selected[area]]
    summary = {
        area: {
            "booklet_code": int(rows[0]["CO_PROVA"]),
            "total_items": len(rows),
            "annulled_in_official_key": sum(item["annulled_in_official_key"] for item in items if item["area"] == area),
            "excluded_from_psychometrics": sum(item["excluded_from_psychometrics"] for item in items if item["area"] == area),
            "items_with_parameters": sum(item["parameters"] is not None for item in items if item["area"] == area),
        }
        for area, rows in selected.items()
    }
    result = {
        "year": 2025,
        "application": "regular",
        "day": 2,
        "booklet": "5_amarelo",
        "official": False,
        "disclaimer": "Parâmetros de itens publicados pelo Inep; nenhuma nota TRI ou reprodução oficial foi validada para este produto.",
        "sources": {"microdados_sha256": manifest["sha256"], "official_key_sha256": pdf_hash},
        "summary": summary,
        "items": items,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({"output": str(OUTPUT), "summary": result["summary"]}, ensure_ascii=False))
