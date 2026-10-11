"""Mapeia os oito cadernos impressos regulares de 2025 contra PDFs oficiais."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import yaml
from pypdf import PdfReader

from pipelines.inep.download import verify_sha256
from pipelines.inep.import_2025 import ARCHIVE, MANIFEST, ROOT, normalize_item, read_items, sha256

OUTPUT = ROOT / "data/processed/2025/cadernos_regulares.json"
BOOKLETS = {
    "D1_CD1": (1, 1, "AZUL"),
    "D1_CD2": (1, 2, "AMARELA"),
    "D1_CD3": (1, 3, "BRANCA"),
    "D1_CD4": (1, 4, "VERDE"),
    "D2_CD5": (2, 5, "AMARELA"),
    "D2_CD6": (2, 6, "CINZA"),
    "D2_CD7": (2, 7, "AZUL"),
    "D2_CD8": (2, 8, "VERDE"),
}
AREA_RANGES = {"LC": range(1, 46), "CH": range(46, 91),
               "CN": range(91, 136), "MT": range(136, 181)}


def parse_key_text(text: str, day: int) -> dict[tuple[int, str], str]:
    single = re.findall(r"(?m)^(\d{1,3})\s+([A-E]|Anulado)$", text)
    double = re.findall(r"(?m)^([1-5])\s+([A-E])\s+([A-E])$", text)
    key = {(int(position), ""): "X" if answer == "Anulado" else answer
           for position, answer in single}
    if day == 1:
        for position, english, spanish in double:
            key[(int(position), "0")] = english
            key[(int(position), "1")] = spanish
        expected = {(position, language) for position in range(1, 6)
                    for language in ("0", "1")}
        expected |= {(position, "") for position in range(6, 91)}
        if len(single) != 85 or len(double) != 5:
            raise ValueError("Gabarito do primeiro dia sem 85 itens comuns e 5 pares de idiomas")
    else:
        expected = {(position, "") for position in range(91, 181)}
        if len(single) != 90 or double:
            raise ValueError("Gabarito do segundo dia sem 90 posições")
    if set(key) != expected or len(key) != len(single) + 2 * len(double):
        raise ValueError("Posições duplicadas ou ausentes no gabarito oficial")
    return key


def read_key(path: Path, day: int) -> dict[tuple[int, str], str]:
    pdf = PdfReader(str(path))
    if len(pdf.pages) != 1:
        raise ValueError(f"PDF de gabarito com páginas inesperadas: {path.name}")
    return parse_key_text(pdf.pages[0].extract_text(), day)


def select_area(rows: list[dict[str, str]], area: str, color: str,
                key: dict[tuple[int, str], str]) -> tuple[str, list[dict[str, str]]]:
    expected_keys = {pair for pair in key if pair[0] in AREA_RANGES[area]}
    candidates = defaultdict(list)
    for row in rows:
        if row["SG_AREA"] == area and row["TX_COR"].upper() == color:
            candidates[row["CO_PROVA"]].append(row)
    matches = []
    for code, candidate in candidates.items():
        by_key = {(int(row["CO_POSICAO"]), row["TP_LINGUA"]): row for row in candidate}
        if (len(candidate) == len(expected_keys) and set(by_key) == expected_keys
                and all(by_key[pair]["TX_GABARITO"] == key[pair] for pair in expected_keys)):
            matches.append((code, [by_key[pair] for pair in sorted(expected_keys)]))
    if len(matches) != 1:
        raise ValueError(f"{area}/{color}: esperado um código de prova; encontrados {len(matches)}")
    return matches[0]


def run(archive: Path = ARCHIVE, source_dir: Path = ROOT / "data/raw/2025",
        output: Path = OUTPUT) -> dict[str, object]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if not verify_sha256(str(archive), manifest["sha256"]):
        raise ValueError("SHA-256 do microdado diverge do manifesto")
    rows = read_items(archive)
    booklets = []
    seen_items = {}
    for name, (day, number, color) in BOOKLETS.items():
        pdf = source_dir / f"2025_GB_impresso_{name}.pdf"
        if sha256(pdf) != manifest["official_regular_keys"][name]:
            raise ValueError(f"SHA-256 do gabarito diverge: {pdf.name}")
        key = read_key(pdf, day)
        area_records = {}
        for area in (("LC", "CH") if day == 1 else ("CN", "MT")):
            code, selected = select_area(rows, area, color, key)
            items = [normalize_item(row) for row in selected]
            for item in items:
                identity = (item["area"], item["inep_item_id"])
                signature = (item["answer"], item["excluded_from_psychometrics"], item["parameters"])
                if identity in seen_items and seen_items[identity] != signature:
                    raise ValueError(f"Item oficial incoerente entre cadernos: {identity}")
                seen_items[identity] = signature
            area_records[area] = {"booklet_code": int(code), "items": items,
                                  "parameterized_count": sum(item["parameters"] is not None for item in items)}
        booklets.append({"day": day, "number": number, "color": color,
                         "official_key_sha256": manifest["official_regular_keys"][name],
                         "areas": area_records})
    result = {
        "year": 2025, "application": "regular", "official": False,
        "disclaimer": "Mapeamento de itens oficiais; não representa validação nem publicação de notas TRI.",
        "source_microdados_sha256": manifest["sha256"],
        "booklet_count": len(booklets), "distinct_inep_items": len(seen_items),
        "booklets": booklets,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output)
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({
        "output": str(OUTPUT), "booklet_count": result["booklet_count"],
        "distinct_inep_items": result["distinct_inep_items"],
        "codes": [{"day": b["day"], "number": b["number"],
                   "areas": {area: data["booklet_code"] for area, data in b["areas"].items()}}
                  for b in result["booklets"]],
    }, ensure_ascii=False))
