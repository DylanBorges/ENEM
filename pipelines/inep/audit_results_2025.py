"""Confere cobertura de respostas do caderno 5 amarelo sem guardar dados pessoais.

Requer 7-Zip porque RESULTADOS_2025.csv usa Deflate64 no ZIP oficial.
"""

from __future__ import annotations

import csv
import io
import json
import shutil
import subprocess
from pathlib import Path

from pipelines.inep.import_2025 import ARCHIVE, OUTPUT, ROOT
from pipelines.inep.download import verify_sha256

RESULTS_OUTPUT = ROOT / "data/processed/2025/cobertura_resultados_d2_caderno5_amarelo.json"


def _seven_zip() -> str:
    installed = shutil.which("7z") or shutil.which("7za")
    if installed:
        return installed
    windows = Path(r"C:\Program Files\7-Zip\7z.exe")
    if windows.is_file():
        return str(windows)
    raise RuntimeError("7-Zip é necessário para ler RESULTADOS_2025.csv (Deflate64)")


def audit(archive: Path = ARCHIVE, items_file: Path = OUTPUT,
          output: Path = RESULTS_OUTPUT) -> dict[str, object]:
    staged = json.loads(items_file.read_text(encoding="utf-8"))
    if not verify_sha256(str(archive), staged["sources"]["microdados_sha256"]):
        raise ValueError("SHA-256 do pacote diverge da importação auditada")
    booklet = {area: data["booklet_code"] for area, data in staged["summary"].items()}
    keys = {
        area: "".join("X" if item["answer"] is None else item["answer"]
                      for item in staged["items"] if item["area"] == area)
        for area in booklet
    }
    counts = {area: {"present_with_booklet": 0, "valid_response_and_key": 0,
                     "missing_or_invalid": 0} for area in booklet}
    member = "microdados_enem_2025/DADOS/RESULTADOS_2025.csv"
    process = subprocess.Popen([_seven_zip(), "x", "-so", str(archive), member],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert process.stdout is not None
        with io.TextIOWrapper(process.stdout, encoding="latin-1", newline="") as stream:
            reader = csv.DictReader(stream, delimiter=";")
            required = {f"{prefix}_{area}" for area in booklet
                        for prefix in ("CO_PROVA", "TP_PRESENCA", "TX_RESPOSTAS", "TX_GABARITO")}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError("Colunas de resultados esperadas não estão presentes")
            for row in reader:
                for area, code in booklet.items():
                    if row[f"CO_PROVA_{area}"] != str(code) or row[f"TP_PRESENCA_{area}"] != "1":
                        continue
                    counts[area]["present_with_booklet"] += 1
                    responses = row[f"TX_RESPOSTAS_{area}"]
                    key = row[f"TX_GABARITO_{area}"]
                    if len(responses) != 45 or len(key) != 45 or key != keys[area]:
                        counts[area]["missing_or_invalid"] += 1
                        continue
                    counts[area]["valid_response_and_key"] += 1
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        if process.wait() != 0:
            raise RuntimeError(f"7-Zip falhou ao ler resultados: {stderr[-500:]}")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    result = {
        "year": 2025, "application": "regular", "booklet": "5_amarelo",
        "source_microdados_sha256": staged["sources"]["microdados_sha256"],
        "areas": counts,
        "note": "Contagens agregadas; nenhuma resposta individual ou nota foi armazenada.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False))
