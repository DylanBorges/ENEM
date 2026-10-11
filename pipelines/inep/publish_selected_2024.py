"""Publica apenas os dois cadernos regulares de 2024 fornecidos pelo usuário."""

from __future__ import annotations

import json

from pipelines.inep.import_2025 import ROOT
from pipelines.inep.import_selected_2024 import OUTPUT as BOOKLETS_FILE
from pipelines.inep.validate_selected_2024 import OUTPUT as VALIDATION_FILE
from pipelines.inep.publish_regular_2025 import publish

RECEIPT = ROOT / "data/processed/2024/publicacao_banco_local.json"


def run() -> dict:
    return publish(booklets_file=BOOKLETS_FILE, validation_file=VALIDATION_FILE,
                   receipt_file=RECEIPT, year=2024, expected_booklets=2)


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
