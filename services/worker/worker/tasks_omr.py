from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageOps
from typing import Any


def remove_exif_and_load(image_path: str) -> np.ndarray:
    """Remove metadados EXIF por privacidade (LGPD) e converte em imagem BGR do OpenCV."""
    with Image.open(image_path) as pil_img:
        # Normaliza rotação de acordo com EXIF e descarta metadados
        pil_img = ImageOps.exif_transpose(pil_img)
        # Converte para RGB
        rgb_img = pil_img.convert("RGB")
        img_np = np.array(rgb_img)
        # Converte RGB -> BGR para OpenCV
        bgr_img = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        return bgr_img


def process_bubble_sheet_image(
    image: np.ndarray,
    num_questions: int = 10,
    confidence_threshold: float = 0.85,
) -> list[dict[str, Any]]:
    """Executa detecção de bolhas A-E e extrai preenchimento com cálculo de confiança.

    Retorna lista de respostas com confidence e status ('confirmed' ou 'requires_confirmation').
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Threshold adaptativo / Otsu invertido (bolhas preenchidas ficam brancas / valor alto)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    h, w = thresh.shape
    results: list[dict[str, Any]] = []

    # Em um template normalizado, as questões são distribuídas verticalmente e alternativas A..E horizontalmente
    y_step = h / float(num_questions)
    x_step = w / 6.0  # Margem + 5 alternativas (A, B, C, D, E)
    alternatives = ["A", "B", "C", "D", "E"]

    for q_idx in range(num_questions):
        q_pos = q_idx + 1
        y_center = int((q_idx + 0.5) * y_step)
        # Amostra o miolo interno da bolha (raio interno) evitando a linha de contorno
        y_radius = int(0.12 * y_step)
        y_start = max(0, y_center - y_radius)
        y_end = min(h, y_center + y_radius)

        bubble_fill_ratios: list[float] = []

        for alt_idx in range(5):
            x_center = int((alt_idx + 1.2) * x_step)
            x_radius = int(0.12 * x_step)
            x_start = max(0, x_center - x_radius)
            x_end = min(w, x_center + x_radius)

            # Região delimitada estritamente no miolo da bolha
            bubble_roi = thresh[y_start:y_end, x_start:x_end]
            if bubble_roi.size == 0:
                bubble_fill_ratios.append(0.0)
                continue

            fill_ratio = float(np.count_nonzero(bubble_roi) / bubble_roi.size)
            bubble_fill_ratios.append(fill_ratio)

        ratios = np.array(bubble_fill_ratios)
        max_ratio = float(np.max(ratios))
        sorted_indices = np.argsort(ratios)[::-1]

        best_idx = int(sorted_indices[0])
        second_best_idx = int(sorted_indices[1])

        best_alt = alternatives[best_idx]
        second_alt = alternatives[second_best_idx]

        best_val = float(ratios[best_idx])
        second_val = float(ratios[second_best_idx])

        # Se quase nenhum preenchimento (< 0.20), questão em branco
        if best_val < 0.20:
            results.append({
                "position": q_pos,
                "detected_answer": None,
                "confidence": 0.95,
                "status": "confirmed",
                "source": "omr",
            })
            continue

        # Mede separabilidade entre a bolha mais preenchida e a segunda
        separation = best_val - second_val
        # Confiança calculada combinando preenchimento absoluto e separação entre alternativas
        confidence = float(np.clip((separation / (best_val + 1e-6)), 0.0, 1.0))

        # Se houver dupla marcação ou pouca separação (ambiguidade)
        if second_val > 0.35 and separation < 0.15:
            results.append({
                "position": q_pos,
                "detected_answer": None,
                "candidates": [
                    {"answer": best_alt, "confidence": round(best_val, 2)},
                    {"answer": second_alt, "confidence": round(second_val, 2)},
                ],
                "status": "requires_confirmation",
                "source": "omr",
            })
        elif confidence >= confidence_threshold:
            results.append({
                "position": q_pos,
                "detected_answer": best_alt,
                "confidence": round(confidence, 2),
                "status": "confirmed",
                "source": "omr",
            })
        else:
            results.append({
                "position": q_pos,
                "detected_answer": best_alt,
                "confidence": round(confidence, 2),
                "candidates": [
                    {"answer": best_alt, "confidence": round(best_val, 2)},
                    {"answer": second_alt, "confidence": round(second_val, 2)},
                ],
                "status": "requires_confirmation",
                "source": "omr",
            })

    return results


def process_omr_task(image_path: str, num_questions: int = 10) -> list[dict[str, Any]]:
    """Ponto de entrada Celery para leitura de cartão-resposta."""
    img = remove_exif_and_load(image_path)
    return process_bubble_sheet_image(img, num_questions=num_questions)
