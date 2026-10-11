"""Importa provas e gabaritos históricos do ENEM (2017 a 2023) a partir de Provas antigas.

Preserva os exames de 2024 e 2025 que possuem calibrações TRI publicadas.
Copia os cadernos PDF para data/booklets/ para visualização direta pelo estudante.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SOURCE_BASE = ROOT / "Provas antigas/drive-download-20261011T172153Z-1-001"
BOOKLETS_DIR = ROOT / "data/booklets"
DB_PATHS = [
    ROOT / "enem_intelligence.db",
    ROOT / "services/api/enem_intelligence.db",
]


def parse_gab_pdf(path: Path, day: int) -> tuple[dict[int, str], dict[int, tuple[str, str]]]:
    reader = PdfReader(str(path))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)

    annulled_nums = set()
    for m in re.finditer(r"(?:Quest[aã]o|Item)\s+(\d{1,3})\s+Anulad[ao]", text, re.I):
        annulled_nums.add(int(m.group(1)))

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    single: dict[int, str] = {}
    double: dict[int, tuple[str, str]] = {}

    for l in lines:
        m2 = re.match(r"^([1-5])\s+([A-E]|anulad[ao]|\*)\s+([A-E]|anulad[ao]|\*)$", l, re.I)
        if m2 and day == 1:
            pos = int(m2.group(1))
            ans1 = "*" if "anulad" in m2.group(2).lower() or m2.group(2) == "*" else m2.group(2).upper()
            ans2 = "*" if "anulad" in m2.group(3).lower() or m2.group(3) == "*" else m2.group(3).upper()
            double[pos] = (ans1, ans2)
            continue
        m1 = re.match(r"^(\d{1,3})\s+([A-E]|anulad[ao]|\*)$", l, re.I)
        if m1:
            pos = int(m1.group(1))
            ans = "*" if "anulad" in m1.group(2).lower() or m1.group(2) == "*" else m1.group(2).upper()
            single[pos] = ans
            continue
        m_only_num = re.match(r"^(\d{1,3})$", l)
        if m_only_num:
            pos = int(m_only_num.group(1))
            if pos in annulled_nums or (day == 2 and 91 <= pos <= 180) or (day == 1 and 6 <= pos <= 90):
                single[pos] = "*"

    for pos in annulled_nums:
        if pos not in single and (day == 2 or pos > 5):
            single[pos] = "*"

    return single, double


def find_files_for_year(year: int) -> dict:
    ydir = SOURCE_BASE / str(year)
    if not ydir.exists():
        raise FileNotFoundError(f"Diretório para {year} não encontrado: {ydir}")

    # Day 1 Prova
    d1_pvs = [f for f in ydir.glob("**/*D1*.pdf") if "gabarito" not in str(f).lower() and "gb" not in f.name.lower()]
    if not d1_pvs:
        d1_pvs = [f for f in (ydir / "Linguagens e Humanas").glob("*.pdf") if "gabarito" not in str(f).lower() and "gb" not in f.name.lower()]

    # Day 1 Gabarito
    d1_gabs = list(ydir.glob("**/*D1*Gabarito*/*.pdf")) + list(ydir.glob("**/Linguagens*/Gabarito/*.pdf"))

    # Day 2 Prova
    d2_pvs = [f for f in ydir.glob("**/*D2*.pdf") if "gabarito" not in str(f).lower() and "gb" not in f.name.lower()]
    if not d2_pvs:
        d2_pvs = [f for f in (ydir / "Natureza e Matemática").glob("*.pdf") if "gabarito" not in str(f).lower() and "gb" not in f.name.lower()]

    # Day 2 Gabarito
    d2_gabs = list(ydir.glob("**/*D2*Gabarito*/*.pdf")) + list(ydir.glob("**/Natureza*/Gabarito/*.pdf"))

    if not (d1_pvs and d1_gabs and d2_pvs and d2_gabs):
        raise ValueError(f"Arquivos incompletos para o ano {year}: d1_pv={d1_pvs}, d1_gab={d1_gabs}, d2_pv={d2_pvs}, d2_gab={d2_gabs}")

    return {
        "d1_pv": d1_pvs[0],
        "d1_gab": d1_gabs[0],
        "d2_pv": d2_pvs[0],
        "d2_gab": d2_gabs[0],
    }


def import_years(years: list[int] = list(range(2017, 2024))):
    BOOKLETS_DIR.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Also copy 2024 booklets if present
    y2024_dir = SOURCE_BASE / "2024"
    if y2024_dir.exists():
        for pv in y2024_dir.glob("**/*.pdf"):
            if "gabarito" not in str(pv).lower() and "gb" not in pv.name.lower():
                target = BOOKLETS_DIR / pv.name
                shutil.copy2(pv, target)

    for db_path in DB_PATHS:
        if not db_path.exists():
            continue
        print(f"\nProcessando banco de dados: {db_path}")
        con = sqlite3.connect(db_path)
        cur = con.cursor()

        for year in years:
            print(f"\n--- Importando ENEM {year} ---")
            files = find_files_for_year(year)

            # Copy PDFs
            d1_dest_name = f"{year}_PV_impresso_D1_CD1.pdf"
            d2_dest_name = f"{year}_PV_impresso_D2_CD5.pdf"
            shutil.copy2(files["d1_pv"], BOOKLETS_DIR / d1_dest_name)
            shutil.copy2(files["d2_pv"], BOOKLETS_DIR / d2_dest_name)
            print(f"  Cadernos PDF copiados para {BOOKLETS_DIR.name}/")

            # Parse answer keys
            d1_single, d1_double = parse_gab_pdf(files["d1_gab"], 1)
            d2_single, _ = parse_gab_pdf(files["d2_gab"], 2)

            if len(d1_single) != 85 or len(d1_double) != 5:
                raise ValueError(f"Ano {year} D1: contagem incorreta (single={len(d1_single)}, double={len(d1_double)})")
            if len(d2_single) != 90:
                raise ValueError(f"Ano {year} D2: contagem incorreta (single={len(d2_single)})")

            # Check existing exam
            cur.execute("SELECT id FROM exams WHERE year = ? AND application = 'regular'", (year,))
            row = cur.fetchone()
            if row:
                exam_id = row[0]
                print(f"  Exame {year} já existia (id={exam_id}). Limpando itens/cadernos antigos para recriar...")
                cur.execute("DELETE FROM booklet_items WHERE booklet_id IN (SELECT id FROM booklets WHERE exam_id = ?)", (exam_id,))
                cur.execute("DELETE FROM booklets WHERE exam_id = ?", (exam_id,))
                cur.execute("DELETE FROM items WHERE exam_id = ?", (exam_id,))
                cur.execute("DELETE FROM exams WHERE id = ?", (exam_id,))

            # Create Exam
            exam_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO exams (id, year, application, title, is_active, created_at, updated_at)
                VALUES (?, ?, 'regular', ?, 1, ?, ?)
                """,
                (exam_id, year, f"ENEM {year} — Aplicação regular (Inep)", now_iso, now_iso),
            )

            # Create Items
            # Day 1:
            # 1..5 English: area LC
            # 1..5 Spanish: area LC
            # 6..45 Common: area LC
            # 46..90 Common: area CH
            # Day 2:
            # 91..135 Common: area CN
            # 136..180 Common: area MT
            items_map = {}  # key -> item_id

            # English items 1..5
            for pos in range(1, 6):
                itm_id = str(uuid.uuid4())
                code = f"ITEM_{year}_LC_{pos}_EN"
                cur.execute(
                    "INSERT INTO items (id, exam_id, area, official_item_code, skill_code, created_at, updated_at) VALUES (?, ?, 'LC', ?, NULL, ?, ?)",
                    (itm_id, exam_id, code, now_iso, now_iso),
                )
                items_map[("D1", "EN", pos)] = itm_id

            # Spanish items 1..5
            for pos in range(1, 6):
                itm_id = str(uuid.uuid4())
                code = f"ITEM_{year}_LC_{pos}_ES"
                cur.execute(
                    "INSERT INTO items (id, exam_id, area, official_item_code, skill_code, created_at, updated_at) VALUES (?, ?, 'LC', ?, NULL, ?, ?)",
                    (itm_id, exam_id, code, now_iso, now_iso),
                )
                items_map[("D1", "ES", pos)] = itm_id

            # LC 6..45
            for pos in range(6, 46):
                itm_id = str(uuid.uuid4())
                code = f"ITEM_{year}_LC_{pos}"
                cur.execute(
                    "INSERT INTO items (id, exam_id, area, official_item_code, skill_code, created_at, updated_at) VALUES (?, ?, 'LC', ?, NULL, ?, ?)",
                    (itm_id, exam_id, code, now_iso, now_iso),
                )
                items_map[("D1", "COMMON", pos)] = itm_id

            # CH 46..90
            for pos in range(46, 91):
                itm_id = str(uuid.uuid4())
                code = f"ITEM_{year}_CH_{pos}"
                cur.execute(
                    "INSERT INTO items (id, exam_id, area, official_item_code, skill_code, created_at, updated_at) VALUES (?, ?, 'CH', ?, NULL, ?, ?)",
                    (itm_id, exam_id, code, now_iso, now_iso),
                )
                items_map[("D1", "COMMON", pos)] = itm_id

            # CN 91..135
            for pos in range(91, 136):
                itm_id = str(uuid.uuid4())
                code = f"ITEM_{year}_CN_{pos}"
                cur.execute(
                    "INSERT INTO items (id, exam_id, area, official_item_code, skill_code, created_at, updated_at) VALUES (?, ?, 'CN', ?, NULL, ?, ?)",
                    (itm_id, exam_id, code, now_iso, now_iso),
                )
                items_map[("D2", "COMMON", pos)] = itm_id

            # MT 136..180
            for pos in range(136, 181):
                itm_id = str(uuid.uuid4())
                code = f"ITEM_{year}_MT_{pos}"
                cur.execute(
                    "INSERT INTO items (id, exam_id, area, official_item_code, skill_code, created_at, updated_at) VALUES (?, ?, 'MT', ?, NULL, ?, ?)",
                    (itm_id, exam_id, code, now_iso, now_iso),
                )
                items_map[("D2", "COMMON", pos)] = itm_id

            # Booklets Day 1
            for lang_code, lang_name, lang_upper in [("EN", "Inglês", "INGLES"), ("ES", "Espanhol", "ESPANHOL")]:
                b_id = str(uuid.uuid4())
                desc = f"Caderno 1 — Azul — {lang_name}"
                cur.execute(
                    """
                    INSERT INTO booklets (id, exam_id, day, color, language, description, created_at, updated_at)
                    VALUES (?, ?, 1, 'Azul', ?, ?, ?, ?)
                    """,
                    (b_id, exam_id, lang_upper, desc, now_iso, now_iso),
                )
                # Booklet items 1..5
                for pos in range(1, 6):
                    ans = d1_double[pos][0] if lang_code == "EN" else d1_double[pos][1]
                    cur.execute(
                        """
                        INSERT INTO booklet_items (id, booklet_id, item_id, physical_position, answer_key, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (str(uuid.uuid4()), b_id, items_map[("D1", lang_code, pos)], pos, ans, now_iso, now_iso),
                    )
                # Booklet items 6..90
                for pos in range(6, 91):
                    ans = d1_single[pos]
                    cur.execute(
                        """
                        INSERT INTO booklet_items (id, booklet_id, item_id, physical_position, answer_key, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (str(uuid.uuid4()), b_id, items_map[("D1", "COMMON", pos)], pos, ans, now_iso, now_iso),
                    )

            # Booklet Day 2: Amarelo
            b2_id = str(uuid.uuid4())
            desc2 = "Caderno 5 — Amarelo"
            cur.execute(
                """
                INSERT INTO booklets (id, exam_id, day, color, language, description, created_at, updated_at)
                VALUES (?, ?, 2, 'Amarelo', NULL, ?, ?, ?)
                """,
                (b2_id, exam_id, desc2, now_iso, now_iso),
            )
            for pos in range(91, 181):
                ans = d2_single[pos]
                cur.execute(
                    """
                    INSERT INTO booklet_items (id, booklet_id, item_id, physical_position, answer_key, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), b2_id, items_map[("D2", "COMMON", pos)], pos, ans, now_iso, now_iso),
                )

            print(f"  ENEM {year} importado com sucesso: 3 cadernos (Dia 1 Inglês/Espanhol + Dia 2 Amarelo) e 185 itens.")

        con.commit()
        con.close()
        print(f"Banco {db_path} atualizado e comitado com sucesso!")


if __name__ == "__main__":
    import_years()
