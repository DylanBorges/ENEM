import os
import yaml
import numpy as np
from typing import Any


def parse_responses_and_keys(respostas: str, gabarito: str) -> list[int | None]:
    """Compara respostas sem converter anulações em acertos."""
    if len(respostas) != len(gabarito):
        raise ValueError("Resposta e gabarito têm comprimentos diferentes")
    vector: list[int | None] = []
    for i in range(len(respostas)):
        r = respostas[i].upper()
        g = gabarito[i].upper()
        if g in {"*", "X"}:
            vector.append(None)
        elif r == g:
            vector.append(1)
        else:
            vector.append(0)
    return vector


def normalize_area_records(
    schema_path: str,
    raw_records: list[dict[str, Any]],
    area: str = "MT",
) -> list[dict[str, Any]]:
    """Normaliza registros brutos de microdados aplicando o schema da edição correspondente."""
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    if area not in schema["areas"]:
        raise ValueError(f"Área desconhecida {area} no schema {schema_path}")

    area_cols = schema["areas"][area]
    presenca_col = area_cols["presenca"]
    resp_col = area_cols["respostas"]
    gab_col = area_cols["gabarito"]
    nota_col = area_cols["nota_oficial"]

    normalized = []
    for rec in raw_records:
        # Participante esteve presente na prova (TP_PRESENCA == 1)
        if rec.get(presenca_col) not in (1, "1"):
            continue

        resp_str = str(rec.get(resp_col, ""))
        gab_str = str(rec.get(gab_col, ""))
        nota_val = rec.get(nota_col)

        if not resp_str or not gab_str or nota_val is None:
            continue

        try:
            official_score = float(nota_val)
        except ValueError:
            continue

        try:
            vector = parse_responses_and_keys(resp_str, gab_str)
        except ValueError:
            continue
        normalized.append({
            "vector": vector,
            "raw_correct": sum(value or 0 for value in vector),
            "official_score": official_score,
            "booklet_code": rec.get(area_cols["caderno"]),
        })

    return normalized
