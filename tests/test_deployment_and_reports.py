from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_MD = ROOT / "docs" / "render_deployment.md"
SRS_PDF = ROOT / "reports" / "PhishShift_SRS.pdf"
FINAL_PDF = ROOT / "reports" / "PhishShift_Final_Report.pdf"


def test_render_docs_exist():
    assert DEPLOY_MD.exists(), "Render deployment guide should exist"
    text = DEPLOY_MD.read_text(encoding="utf-8")
    assert "Render" in text and "gunicorn" in text.lower()


def test_pdf_reports_exist():
    assert SRS_PDF.exists(), "SRS PDF should exist"
    assert FINAL_PDF.exists(), "Final report PDF should exist"
