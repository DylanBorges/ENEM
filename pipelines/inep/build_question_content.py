"""Publish native question text and figures from locally reviewed source material.

Run from the repository root after placing the official PDFs/TXT in data/booklets
and the archived enem.dev question JSON in data/processed/enem-dev. The output is
static, so the API never needs the source files or PDF tooling at runtime.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import shutil
import sqlite3
import unicodedata
from urllib.parse import urlparse

import fitz
from rapidfuzz import fuzz
from scipy.optimize import linear_sum_assignment
from .classify_subject import classify_subject

ROOT = Path(__file__).resolve().parents[2]
SOURCE_JSON = ROOT / "data/processed/enem-dev/quiz-items"
BOOKLETS = ROOT / "data/booklets"
CONTENT_PATH = ROOT / "services/api/app/db/question_content.json"
IMAGE_ROOT = ROOT / "apps/web/public/question-images"
HEADING = re.compile(r"(?i)quest.{0,3}o\s*0?([1-9]\d{0,2})\b")
DOSVOX_HEADING = re.compile(r"(?im)^quest[ãa]o\s+0?([1-9]\d{0,2})\s*$")
CHOICE = re.compile(r"(?im)^[ \t]*([a-e])[ \t]*[.)][ \t]+")
MARKDOWN_IMAGE = re.compile(r"!\[[^]]*\]\((https?://[^)]+)\)")


def key(year: int, position: int, language: str | None) -> str:
    return f"{year}-{position}-{language or 'NONE'}"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def decode_2018_pdf_text(value: str) -> str:
    """Undo the shifted glyph encoding in part of the 2018 printed PDF.

    This is only used to match a caderno position to a separately transcribed
    item. The decoded PDF text is never published as a question statement.
    """
    lines = []
    for line in value.splitlines():
        if "\x03" in line:
            decoded = []
            for character in line:
                if "A" <= character <= "Z":
                    decoded.append(chr((ord(character) - ord("A") - 3) % 26 + ord("A")))
                elif "a" <= character <= "z":
                    decoded.append(chr((ord(character) - ord("a") - 3) % 26 + ord("a")))
                else:
                    decoded.append({"\x03": " ", "\x0f": ",", "\x11": ".", "\x10": "-"}.get(character, character))
            line = "".join(decoded)
        lines.append(line)
    return "\n".join(lines)


def official_mappings() -> dict[tuple[int, int, str | None], str]:
    connection = sqlite3.connect(ROOT / "enem_intelligence.db")
    rows = connection.execute("""
        SELECT e.year, bi.physical_position, b.language, bi.answer_key
        FROM booklet_items bi JOIN booklets b ON b.id = bi.booklet_id
        JOIN exams e ON e.id = b.exam_id
        WHERE lower(b.color) IN ('azul', 'amarelo')
        ORDER BY e.year, bi.physical_position, b.color != 'Azul'
    """).fetchall()
    result = {}
    for year, position, language, answer in rows:
        result.setdefault((year, position, language if position <= 5 else None), answer.upper())
    return result


def reference_item_codes() -> dict[tuple[int, int, str | None], str]:
    connection = sqlite3.connect(ROOT / "enem_intelligence.db")
    rows = connection.execute("""
        SELECT e.year, bi.physical_position, b.language, i.official_item_code
        FROM booklet_items bi JOIN booklets b ON b.id = bi.booklet_id
        JOIN exams e ON e.id = b.exam_id JOIN items i ON i.id = bi.item_id
        WHERE lower(b.color) IN ('azul', 'amarelo')
        ORDER BY e.year, bi.physical_position, b.color != 'Azul'
    """).fetchall()
    result = {}
    for year, position, language, code in rows:
        result.setdefault((year, position, language if position <= 5 else None), code)
    return result


def local_image(url: str, year: int, position: int, language: str | None) -> str:
    name = Path(urlparse(url).path).name
    folder = f"{position}-{(language or '').lower()}".rstrip("-")
    source = SOURCE_JSON / str(year) / "questions" / folder / name
    if not source.is_file():
        raise FileNotFoundError(source)
    output_name = Path(name).with_suffix(".png").name if name.endswith(".latex") else name
    destination = IMAGE_ROOT / str(year) / folder / output_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if name.endswith(".latex"):
        from PIL import Image
        with Image.open(source) as image:
            image.save(destination, "PNG")
    else:
        shutil.copyfile(source, destination)
    return f"/question-images/{year}/{folder}/{output_name}"


def image_exists(url: str, year: int, position: int, language: str | None) -> bool:
    folder = f"{position}-{(language or '').lower()}".rstrip("-")
    return (SOURCE_JSON / str(year) / "questions" / folder / Path(urlparse(url).path).name).is_file()


def structured_record(data: dict, year: int, target_position: int, language: str | None, answer: str) -> dict | None:
    source_position = int(data["index"])
    source_language = (data.get("language") or "").upper() or None
    alternatives = data.get("alternatives") or []
    if [a.get("letter") for a in alternatives] != list("ABCDE"):
        return None
    context = data.get("context") or ""
    image_urls = MARKDOWN_IMAGE.findall(context) + [a["file"] for a in alternatives if a.get("file")]
    if any(not image_exists(url, year, source_position, source_language) for url in image_urls):
        return None
    blocks = []
    start = 0
    for match in MARKDOWN_IMAGE.finditer(context):
        text = context[start:match.start()].strip()
        if text:
            blocks.append({"type": "text", "value": text})
        blocks.append({"type": "image", "value": local_image(match.group(1), year, source_position, source_language)})
        start = match.end()
    tail = context[start:].strip()
    if tail:
        blocks.append({"type": "text", "value": tail})
    intro = (data.get("alternativesIntroduction") or "").strip()
    if intro:
        blocks.append({"type": "text", "value": intro})
    options = []
    for alternative in alternatives:
        image = alternative.get("file")
        options.append({
            "letter": alternative["letter"],
            "text": (alternative.get("text") or "").strip(),
            "image": local_image(image, year, source_position, source_language) if image else None,
        })
    if not blocks or not all(a["text"] or a["image"] for a in options):
        return None
    return {"blocks": blocks, "alternatives": options, "answer_key": answer,
            "source": "enem.dev (transcrição dos cadernos do Inep)", "source_number": source_position}


def structured_questions(answer_keys: dict) -> dict:
    result = {}
    for year in range(2017, 2024):
        source_data = {}
        for path in sorted((SOURCE_JSON / str(year) / "questions").glob("*/details.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            position = int(data["index"])
            language = (data.get("language") or "").upper() or None
            if position <= 90:
                if position > 5:
                    language = None
                expected = answer_keys.get((year, position, language))
                if expected is None or data.get("correctAlternative", "").upper() != expected:
                    continue
                record = structured_record(data, year, position, language, expected)
                if record:
                    result[key(year, position, language)] = record
            else:
                source_data[position] = data
        document, blue = pdf_questions(year, 2)
        orange = [{"number": number, "occurrence": 1,
                   "statement": (data.get("context") or "") + " " + (data.get("alternativesIntroduction") or ""),
                   "alternatives": [{"text": alternative.get("text") or ""} for alternative in data.get("alternatives") or []]}
                  for number, data in source_data.items()]
        for target, source, score in match_covers(blue, orange):
            minimum_score, minimum_margin = (55, 12) if year == 2018 else (60, 15)
            if score < 80 and (score < minimum_score or match_margin(target, source, orange, score) < minimum_margin):
                continue
            data = source_data[source["number"]]
            answer = (data.get("correctAlternative") or "").upper()
            if answer not in "ABCDE":
                continue
            record = structured_record(data, year, target["number"], None, answer)
            if record:
                record["match_score"] = round(score, 1)
                result[key(year, target["number"], None)] = record
        document.close()
    return result


def dosvox_questions(year: int, day: int) -> list[dict]:
    if year == 2023:
        areas = ("LC", "CH") if day == 1 else ("CN", "MT")
        paths = [next(BOOKLETS.glob(f"{year}_Dia_{day}_P1_{area}_*DOSVOX.txt")) for area in areas]
        text = "\n".join(path.read_bytes().decode("cp1252") for path in paths)
    else:
        path = next(BOOKLETS.glob(f"{year}_Dia_{day}*DOSVOX.txt"))
        text = path.read_bytes().decode("cp1252")
    headings = list(DOSVOX_HEADING.finditer(text))
    counts = defaultdict(int)
    result = []
    for index, heading in enumerate(headings):
        position = int(heading.group(1))
        counts[position] += 1
        body = text[heading.end():headings[index + 1].start() if index + 1 < len(headings) else len(text)].strip()
        choices = list(CHOICE.finditer(body))
        if [choice.group(1).upper() for choice in choices] != list("ABCDE"):
            raise ValueError(f"Alternativas incompletas no DOSVOX {year} dia {day} questão {position}")
        statement = body[:choices[0].start()].strip()
        alternatives = []
        for i, choice in enumerate(choices):
            end = choices[i + 1].start() if i + 1 < len(choices) else len(body)
            alternative_text = re.sub(r"\s*\(Fim da prova\)\s*$", "", body[choice.end():end], flags=re.IGNORECASE).strip()
            alternatives.append({"letter": choice.group(1).upper(), "text": alternative_text, "image": None})
        result.append({"number": position, "occurrence": counts[position], "statement": statement, "alternatives": alternatives})
    return result


def pdf_questions(year: int, day: int, color: str = "blue") -> tuple[fitz.Document, list[dict]]:
    filename = (next(BOOKLETS.glob(f"{year}_PV*D{day}*.pdf")) if color == "blue"
                else BOOKLETS / f"{year}_PV_D{day}_CD{9 if day == 1 else 11}_LARANJA.pdf")
    document = fitz.open(filename)
    questions = []
    counts = defaultdict(int)
    current = None
    for page_index, page in enumerate(document):
        blocks = [block for block in page.get_text("blocks") if block[1] < 742 and block[3] > 55 and block[6] == 0]
        blocks.sort(key=lambda block: (block[0] >= page.rect.width * .45, block[1]))
        for block in blocks:
            heading = HEADING.search(block[4])
            number = int(heading.group(1)) if heading else None
            if number is not None and (1 <= number <= 90 if day == 1 else 91 <= number <= 180):
                if current is not None and heading.start():
                    current["text"] += " " + block[4][:heading.start()]
                counts[number] += 1
                current = {"number": number, "occurrence": counts[number], "text": block[4][heading.start():],
                           "page": page_index, "column": block[0] >= page.rect.width * .45,
                           "top": block[1], "bottom": 742.0}
                for earlier in reversed(questions):
                    if earlier["page"] == page_index and earlier["column"] == current["column"]:
                        earlier["bottom"] = block[1] - 3
                        break
                questions.append(current)
            elif current is not None:
                current["text"] += " " + block[4]
    if year == 2018:
        for question in questions:
            question["text"] = decode_2018_pdf_text(question["text"])
    return document, questions


def orange_answer_keys(year: int, day: int) -> dict[tuple[int, int], str]:
    path = next(BOOKLETS.glob(f"{year}_GB_D{day}_CD{9 if day == 1 else 11}*.pdf"))
    text = "\n".join(page.get_text() for page in fitz.open(path))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result = {}
    for index, line in enumerate(lines):
        if not line.isdigit():
            continue
        number = int(line)
        if not (1 <= number <= 90 if day == 1 else 91 <= number <= 180):
            continue
        if index + 1 >= len(lines) or lines[index + 1] not in (*"ABCDE", "Anulado"):
            continue
        result[(number, 1)] = "*" if lines[index + 1] == "Anulado" else lines[index + 1]
        if day == 1 and number <= 5 and index + 2 < len(lines) and lines[index + 2] in "ABCDE":
            result[(number, 2)] = lines[index + 2]
    return result


def same_area(blue: dict, orange: dict) -> bool:
    a, b = blue["number"], orange["number"]
    if a <= 5 or b <= 5:
        return a <= 5 and b <= 5 and blue["occurrence"] == orange["occurrence"]
    return any(low <= a <= high and low <= b <= high for low, high in ((6, 45), (46, 90), (91, 135), (136, 180)))


def match_covers(blue: list[dict], orange: list[dict]) -> list[tuple[dict, dict, float]]:
    scores = []
    for b in blue:
        text = normalize(b["text"])
        scores.append([fuzz.token_set_ratio(text, normalize(o["statement"] + " " + " ".join(a["text"] for a in o["alternatives"])))
                       if same_area(b, o) else -1000 for o in orange])
    import numpy as np
    row_indices, column_indices = linear_sum_assignment(-np.asarray(scores))
    return [(blue[r], orange[c], scores[r][c]) for r, c in zip(row_indices, column_indices)]


def match_margin(target: dict, source: dict, candidates: list[dict], score: float) -> float:
    other_scores = [fuzz.token_set_ratio(
        normalize(target["text"]),
        normalize(candidate["statement"] + " " + " ".join(a["text"] for a in candidate["alternatives"])),
    ) for candidate in candidates if candidate is not source and same_area(target, candidate)]
    return score - max(other_scores, default=0)


def question_figure(document: fitz.Document, orange_pdf: dict, year: int, day: int, source_number: int, occurrence: int) -> str:
    page = document[orange_pdf["page"]]
    left = page.rect.width * (.48 if orange_pdf["column"] else .035)
    right = page.rect.width * (.97 if orange_pdf["column"] else .52)
    figures = []
    for image in page.get_images(full=True):
        for bounds in page.get_image_rects(image[0]):
            if bounds.width < 35 or bounds.height < 20 or bounds.width * bounds.height < 700:
                continue
            if bounds.y0 < orange_pdf["top"] or bounds.y1 > orange_pdf["bottom"]:
                continue
            center = (bounds.x0 + bounds.x1) / 2
            if orange_pdf["column"] and center < page.rect.width * .3:
                continue
            if not orange_pdf["column"] and center > page.rect.width * .7:
                continue
            figures.append(bounds)
    if figures:
        rect = fitz.Rect(min(bound.x0 for bound in figures) - 4, min(bound.y0 for bound in figures) - 4,
                         max(bound.x1 for bound in figures) + 4, max(bound.y1 for bound in figures) + 4) & page.rect
    else:
        # Vector art and diagrams do not appear in get_images; retain their local
        # question region as a visual supplement to the selectable native text.
        rect = fitz.Rect(left, max(72, orange_pdf["top"] - 3), right, max(orange_pdf["top"] + 10, orange_pdf["bottom"]))
    pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), clip=rect, alpha=False)
    filename = f"{source_number}-{occurrence}.webp"
    destination = IMAGE_ROOT / str(year) / f"day-{day}" / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    # PyMuPDF writes PNG; PIL converts to a smaller web image.
    from PIL import Image
    import io
    Image.open(io.BytesIO(pix.tobytes("png"))).save(destination, "WEBP", quality=82)
    return f"/question-images/{year}/day-{day}/{filename}"


def recent_questions() -> tuple[dict, Counter]:
    result = {}
    audit = Counter()
    for year in (2023, 2024, 2025):
        for day in (1, 2):
            orange = dosvox_questions(year, day)
            blue_doc, blue = pdf_questions(year, day)
            orange_doc, orange_pdf = pdf_questions(year, day, "orange")
            official_keys = orange_answer_keys(year, day)
            pdf_by_number = {(q["number"], q["occurrence"]): q for q in orange_pdf}
            assert len(orange) == len(blue) == len(orange_pdf) == (95 if day == 1 else 90)
            for target, source, score in match_covers(blue, orange):
                if score < 72 and (score < 60 or match_margin(target, source, orange, score) < 15):
                    audit[f"{year} low match"] += 1
                    continue
                other = pdf_by_number.get((source["number"], source["occurrence"]))
                answer = official_keys.get((source["number"], source["occurrence"]))
                if other is None or answer is None:
                    audit[f"{year} missing source"] += 1
                    continue
                language = ("INGLES" if target["occurrence"] == 1 else "ESPANHOL") if target["number"] <= 5 else None
                blocks = [{"type": "text", "value": source["statement"]}]
                visual_text = source["statement"] + " " + " ".join(option["text"] for option in source["alternatives"])
                if "descri" in visual_text.lower() and re.search(r"(?i)imagem|figura|fotograf|gr[áa]fic|tabela|mapa|quadr|diagrama|esquema", visual_text):
                    blocks.append({"type": "image", "value": question_figure(orange_doc, other, year, day, source["number"], source["occurrence"]),
                                   "alt": "Figura no caderno oficial. A descrição também está no enunciado."})
                result[key(year, target["number"], language)] = {
                    "blocks": blocks, "alternatives": source["alternatives"], "answer_key": answer,
                    "source": "Inep, transcrição DOSVOX e caderno laranja oficial",
                    "source_number": source["number"], "match_score": round(score, 1),
                }
                audit[f"{year} published"] += 1
            blue_doc.close()
            orange_doc.close()
    return result, audit


def main() -> None:
    answer_keys = official_mappings()
    codes = reference_item_codes()
    data = structured_questions(answer_keys)
    recent, audit = recent_questions()
    for item_key, record in recent.items():
        data.setdefault(item_key, record)
    for item_key, record in data.items():
        _, position_text, language = item_key.split("-", 2)
        position = int(position_text)
        area = "LC" if position <= 45 else "CH" if position <= 90 else "CN" if position <= 135 else "MT"
        wording = " ".join(block["value"] for block in record["blocks"] if block["type"] == "text")
        record["subject"] = classify_subject(area, wording, position, None if language == "NONE" else language)
        record["official_item_code"] = codes.get((int(item_key[:4]), position, None if language == "NONE" else language))
        record["source_booklet"] = ("caderno Azul" if int(item_key[:4]) <= 2023 and position <= 90
                                    else "acervo enem.dev" if int(item_key[:4]) <= 2023 else "caderno Laranja")
    CONTENT_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(data)} questões com conteúdo nativo; {dict(audit)}")


if __name__ == "__main__":
    main()
