from typing import Any


def run_async_essay_analysis_task(
    essay_text: str,
    rubric_year: int = 2026,
) -> dict[str, Any]:
    """Tarefa assíncrona Celery para extração de features e análise de redação."""
    words = essay_text.split()
    word_count = len(words)

    # Identificação de parágrafos
    paragraphs = [p.strip() for p in essay_text.split("\n\n") if p.strip()]

    return {
        "word_count": word_count,
        "paragraph_count": len(paragraphs),
        "status": "ready_for_grading",
    }
