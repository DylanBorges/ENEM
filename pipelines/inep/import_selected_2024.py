"""Cruza os dois cadernos 2024 enviados pelo usuário com microdados do Inep."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import yaml

from pipelines.inep.download import verify_sha256
from pipelines.inep.import_2025 import ROOT, normalize_item, sha256
from pipelines.inep.import_regular_2025 import read_key, select_area

ARCHIVE = ROOT / "data/raw/2024/microdados_enem_2024.zip"
MANIFEST = ROOT / "pipelines/inep/manifests/2024.yaml"
OUTPUT = ROOT / "data/processed/2024/cadernos_selecionados.json"
BOOKLETS = ((1, 1, ("LC", "CH")), (2, 7, ("CN", "MT")))


def read_items(archive: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(archive) as source:
        names = [name for name in source.namelist() if name.endswith("/DADOS/ITENS_PROVA_2024.csv")]
        if len(names) != 1:
            raise ValueError("Tabela ITENS_PROVA_2024 não encontrada de forma única")
        with source.open(names[0]) as raw:
            with io.TextIOWrapper(raw, encoding="latin-1", newline="") as stream:
                return list(csv.DictReader(stream, delimiter=";"))


def run(archive: Path = ARCHIVE, source_dir: Path = ROOT / "data/raw/2024",
        output: Path = OUTPUT) -> dict[str, object]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if not verify_sha256(str(archive), manifest["sha256"]):
        raise ValueError("SHA-256 do pacote 2024 diverge do manifesto")
    rows = read_items(archive)
    booklets = []
    identities = {}
    for day, number, areas in BOOKLETS:
        pdf_name = f"2024_GB_impresso_D{day}_CD{number}.pdf"
        pdf = source_dir / pdf_name
        expected_hash = manifest["official_regular_keys"][f"D{day}_CD{number}"]
        if sha256(pdf) != expected_hash:
            raise ValueError(f"PDF oficial de 2024 alterado: {pdf_name}")
        key = read_key(pdf, day)
        area_data = {}
        for area in areas:
            code, selected = select_area(rows, area, "AZUL", key)
            items = [normalize_item(row) for row in selected]
            for item in items:
                identity = (item["area"], item["inep_item_id"])
                signature = (item["answer"], item["excluded_from_psychometrics"], item["parameters"])
                if identity in identities and identities[identity] != signature:
                    raise ValueError(f"Item incoerente entre cadernos: {identity}")
                identities[identity] = signature
            area_data[area] = {"booklet_code": int(code), "items": items,
                               "parameterized_count": sum(item["parameters"] is not None for item in items)}
        booklets.append({"day": day, "number": number, "color": "AZUL",
                         "official_key_sha256": expected_hash, "areas": area_data})
    result = {
        "year": 2024, "application": "regular", "official": False,
        "disclaimer": "Mapeamento de itens oficiais; não representa nota oficial nem validação de escala.",
        "source_microdados_sha256": manifest["sha256"],
        "booklet_count": len(booklets), "distinct_inep_items": len(identities),
        "booklets": booklets,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({"output": str(OUTPUT), "booklet_count": result["booklet_count"],
                      "distinct_inep_items": result["distinct_inep_items"],
                      "codes": {str(b["day"]): {area: data["booklet_code"]
                                                 for area, data in b["areas"].items()}
                                for b in result["booklets"]}}, ensure_ascii=False))
