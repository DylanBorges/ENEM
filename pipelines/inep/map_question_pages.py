"""Generate page anchors for locally held official ENEM booklets.

Only question numbers and PDF page numbers are exported; PDF content stays local.
Run from the repository root with: python -m pipelines.inep.map_question_pages
"""

import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/booklets"
DESTINATION = ROOT / "services/api/app/db/question_pages.json"
FILENAME = re.compile(r"^(\d{4})_PV_impresso_D([12])_CD\d+\.pdf$")
HEADING = re.compile(r"Q\s*U\s*E\s*S\s*T\s*.\s*O\s+0?([1-9]\d{0,2})\b", re.IGNORECASE)


def build_page_map() -> dict[str, dict[str, int]]:
    result = {}
    for path in sorted(SOURCE.glob("*.pdf")):
        match = FILENAME.match(path.name)
        if not match:
            continue
        year, day = map(int, match.groups())
        pages = {}
        for page_number, page in enumerate(PdfReader(str(path)).pages, start=1):
            text = page.extract_text() or ""
            for found in HEADING.finditer(text):
                number = int(found.group(1))
                if (1 <= number <= 90 if day == 1 else 91 <= number <= 180):
                    if day == 1 and number <= 5 and str(number) in pages:
                        pages[f"ES-{number}"] = page_number
                    pages.setdefault(str(number), page_number)
        result[f"{year}-{day}"] = pages
    return result


if __name__ == "__main__":
    page_map = build_page_map()
    DESTINATION.write_text(json.dumps(page_map, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    for key, pages in page_map.items():
        print(f"{key}: {len(pages)} questões localizadas")
