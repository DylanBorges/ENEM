"""Valida em holdout os dois cadernos de 2024 fornecidos pelo usuário."""

from __future__ import annotations

import json

from pipelines.inep.import_2025 import ROOT
from pipelines.inep.import_selected_2024 import ARCHIVE, OUTPUT as BOOKLETS_FILE
from pipelines.inep.validate_official_2025 import run as validate

OUTPUT = ROOT / "data/processed/2024/validacao_notas_selecionadas.json"


def run() -> dict[str, object]:
    return validate(archive=ARCHIVE, booklets_file=BOOKLETS_FILE,
                    output=OUTPUT, year=2024, sample_percent=2)


if __name__ == "__main__":
    result = run()
    print(json.dumps({area: {"link": data["link_count"],
                             "holdout": data["holdout_count"],
                             "mae": data["metrics"]["mae"],
                             "correlation": data["metrics"]["correlation"],
                             "release_gate_passed": data["release_gate_passed"]}
                      for area, data in result["areas"].items()}, ensure_ascii=False))
