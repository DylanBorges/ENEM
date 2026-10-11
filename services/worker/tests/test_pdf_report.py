import os
import tempfile
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from worker.tasks_reports import generate_student_pdf_report


def test_generate_student_pdf_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "relatorio_teste.pdf")
        results = [
            {
                "area": "MT",
                "raw_correct": 35,
                "answered_items": 45,
                "theta_eap": 0.8124,
                "posterior_sd": 0.2512,
                "score_estimated": 712.4,
                "credible_interval_95": (660.1, 764.7),
                "coverage": 1.0,
            }
        ]
        out = generate_student_pdf_report(
            output_path=pdf_path,
            student_name="Mariana Silva",
            exam_title="ENEM 2025 Regular",
            results=results,
        )

        assert os.path.exists(out)
        assert os.path.getsize(out) > 1000  # PDF não-vazio gerado
