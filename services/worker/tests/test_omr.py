import cv2
import numpy as np
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from worker.tasks_omr import process_bubble_sheet_image


def generate_synthetic_answer_sheet() -> np.ndarray:
    """Gera imagem sintética de cartão-resposta para validação do pipeline OMR."""
    # Imagem branca 600x400
    img = np.ones((500, 600, 3), dtype=np.uint8) * 255

    num_questions = 5
    y_step = 500 / num_questions
    x_step = 600 / 6.0

    # Desenha contornos de círculos para cada alternativa
    for q in range(num_questions):
        y_center = int((q + 0.5) * y_step)
        for alt_idx in range(5):
            x_center = int((alt_idx + 1.2) * x_step)
            cv2.circle(img, (x_center, y_center), 18, (80, 80, 80), 2)

    # Questão 1 (pos 1): Preenche totalmente a alternativa B (alt_idx = 1)
    y1 = int(0.5 * y_step)
    x1 = int(2.2 * x_step)
    cv2.circle(img, (x1, y1), 16, (10, 10, 10), -1)

    # Questão 2 (pos 2): Preenche totalmente a alternativa D (alt_idx = 3)
    y2 = int(1.5 * y_step)
    x2 = int(4.2 * x_step)
    cv2.circle(img, (x2, y2), 16, (10, 10, 10), -1)

    # Questão 3 (pos 3): Em branco (nenhuma bolha preenchida)

    # Questão 4 (pos 4): Ambiguidade - DUAS bolhas preenchidas (A e C)
    y4 = int(3.5 * y_step)
    xA = int(1.2 * x_step)
    xC = int(3.2 * x_step)
    cv2.circle(img, (xA, y4), 16, (15, 15, 15), -1)
    cv2.circle(img, (xC, y4), 16, (15, 15, 15), -1)

    # Questão 5 (pos 5): Bolha fraca / cinza claro (alt_idx = 2 / C)
    y5 = int(4.5 * y_step)
    x5 = int(3.2 * x_step)
    cv2.circle(img, (x5, y5), 14, (180, 180, 180), -1)

    return img


def test_synthetic_omr_detection():
    synthetic_img = generate_synthetic_answer_sheet()
    results = process_bubble_sheet_image(
        synthetic_img,
        num_questions=5,
        confidence_threshold=0.80,
    )

    assert len(results) == 5

    # Questão 1: B confirmada
    q1 = results[0]
    assert q1["position"] == 1
    assert q1["detected_answer"] == "B"
    assert q1["status"] == "confirmed"

    # Questão 2: D confirmada
    q2 = results[1]
    assert q2["position"] == 2
    assert q2["detected_answer"] == "D"
    assert q2["status"] == "confirmed"

    # Questão 3: Em branco
    q3 = results[2]
    assert q3["position"] == 3
    assert q3["detected_answer"] is None
    assert q3["status"] == "confirmed"

    # Questão 4: Ambiguidade / duas bolhas preenchidas -> status requires_confirmation
    q4 = results[3]
    assert q4["position"] == 4
    assert q4["status"] == "requires_confirmation"
    assert "candidates" in q4
    candidate_letters = [c["answer"] for c in q4["candidates"]]
    assert "A" in candidate_letters or "C" in candidate_letters
