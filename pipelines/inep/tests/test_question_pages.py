import json
from pathlib import Path


def test_official_question_page_map_covers_imported_exam_years():
    root = Path(__file__).resolve().parents[3]
    page_map = json.loads((root / "services/api/app/db/question_pages.json").read_text(encoding="utf-8"))
    assert set(page_map) == {f"{year}-{day}" for year in range(2017, 2026) for day in (1, 2)}
    for year in range(2017, 2026):
        day_one = page_map[f"{year}-1"]
        day_two = page_map[f"{year}-2"]
        assert all(str(position) in day_one for position in range(1, 91))
        assert all(f"ES-{position}" in day_one for position in range(1, 6))
        assert all(str(position) in day_two for position in range(91, 181))
        assert all(page > 0 for page in (*day_one.values(), *day_two.values()))
