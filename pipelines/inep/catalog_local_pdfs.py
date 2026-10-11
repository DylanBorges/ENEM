"""Inventaria PDFs fornecidos pelo usuário sem copiar o conteúdo das provas."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from pipelines.inep.import_2025 import ROOT

SOURCE = ROOT / "Provas antigas"
OUTPUT = ROOT / "data/processed/catalogo_provas_locais.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def catalog(source: Path = SOURCE, output: Path = OUTPUT) -> dict[str, object]:
    if not source.is_dir():
        raise FileNotFoundError(f"Pasta de provas ausente: {source}")
    files = []
    for path in sorted(source.rglob("*.pdf")):
        relative = path.relative_to(source)
        year_parts = [part for part in relative.parts if re.match(r"^20\d{2}(?:\s|$)", part)]
        if len(year_parts) != 1:
            raise ValueError(f"Ano ambíguo no caminho: {relative}")
        year_folder = year_parts[0]
        year = int(year_folder[:4])
        application = "reaplicacao_ppl" if "PPL" in year_folder.upper() else "regular"
        is_key = "Gabarito" in relative.parts
        files.append({
            "path": relative.as_posix(),
            "year": year,
            "application": application,
            "year_folder": year_folder,
            "category": relative.parts[-2] if not is_key else relative.parts[-3],
            "kind": "gabarito" if is_key else "prova",
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    groups = defaultdict(lambda: {"provas": 0, "gabaritos": 0})
    for file in files:
        group = groups[(file["year_folder"], file["category"])]
        group["gabaritos" if file["kind"] == "gabarito" else "provas"] += 1
    missing_keys = [
        {"year_folder": year_folder, "category": category, **counts}
        for (year_folder, category), counts in sorted(groups.items())
        if counts["provas"] and not counts["gabaritos"]
    ]
    result = {
        "source_directory": str(source),
        "pdf_count": len(files),
        "years": sorted({file["year"] for file in files}),
        "regular_count": sum(file["application"] == "regular" for file in files),
        "reapplication_count": sum(file["application"] == "reaplicacao_ppl" for file in files),
        "missing_gabarito_groups": missing_keys,
        "files": files,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)
    return result


if __name__ == "__main__":
    result = catalog()
    print(json.dumps({key: result[key] for key in (
        "pdf_count", "years", "regular_count", "reapplication_count", "missing_gabarito_groups"
    )}, ensure_ascii=False))
