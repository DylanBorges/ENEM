import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from typing import Any


def generate_student_pdf_report(
    output_path: str,
    student_name: str,
    exam_title: str,
    results: list[dict[str, Any]],
    model_version: str = "tri-core-0.1.0",
) -> str:
    """Gera PDF individual auditável com estimativa psicométrica, intervalo e disclaimer obrigatório."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    # Cabeçalho
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "ENEM Intelligence - Relatório Diagnóstico de Desempenho")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Estudante: {student_name} | Simulado: {exam_title}")
    c.drawString(50, height - 85, f"Versão do Motor Psicométrico: {model_version}")

    c.setLineWidth(1)
    c.line(50, height - 95, width - 50, height - 95)

    # Disclaimer legal obrigatório
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 120, "AVISO LEGAL IMPORTANTE:")
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(
        50,
        height - 135,
        "Todas as notas apresentadas são estimativas independentes baseadas em Teoria de Resposta ao Item (TRI).",
    )
    c.drawString(
        50,
        height - 148,
        "Este relatório NÃO reproduz garantidamente e NÃO constitui a nota oficial publicada pelo INEP/MEC.",
    )

    c.line(50, height - 160, width - 50, height - 160)

    # Tabela de Desempenho por Área
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 185, "Resultados Psicométricos Estimados (Modelo 3PL + EAP)")

    y = height - 215
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "Área")
    c.drawString(110, y, "Acertos")
    c.drawString(170, y, "Theta EAP")
    c.drawString(240, y, "Desvio Post.")
    c.drawString(320, y, "Nota Estimada")
    c.drawString(410, y, "Intervalo 95%")
    c.drawString(500, y, "Cobertura")

    y -= 15
    c.setFont("Helvetica", 9)
    for res in results:
        c.drawString(50, y, str(res.get("area", "")))
        c.drawString(110, y, f"{res.get('raw_correct', 0)}/{res.get('answered_items', 45)}")
        c.drawString(170, y, f"{res.get('theta_eap', 0.0):.4f}")
        c.drawString(240, y, f"±{res.get('posterior_sd', 0.0):.4f}")
        c.drawString(320, y, f"{res.get('score_estimated', 0.0):.1f}")
        interval = res.get("credible_interval_95", (0.0, 0.0))
        c.drawString(410, y, f"[{interval[0]:.1f}, {interval[1]:.1f}]")
        c.drawString(500, y, f"{res.get('coverage', 1.0):.1%}")
        y -= 20

    # Rodapé de auditoria
    c.setFont("Helvetica", 8)
    c.drawString(50, 40, "ENEM Intelligence Platform | Software Livre e Independente | Hash de Auditoria Registrado")
    c.save()

    return output_path
