from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports"


def build_pdf(path: Path, title: str, sections: list[str]) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=0.75 * inch, leftMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph("Decision support only - not a guarantee of safety.", ParagraphStyle("banner", parent=styles["BodyText"], fontName="Helvetica-Bold", textColor="#7a1d1d")))
    story.append(Spacer(1, 0.2 * inch))
    for section in sections:
        story.append(Paragraph(section, styles["BodyText"]))
        story.append(Spacer(1, 0.15 * inch))
    doc.build(story)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    srs_sections = [
        "PhishShift Message Risk Scanner SRS",
        "",
        "1. Purpose: Provide a synthetic phishing-risk triage tool for helpdesk analysts without opening live URLs or using real data.",
        "2. Scope: Includes synthetic corpus generation, cleaning, deduplication, campaign-grouped splits, rule + TF-IDF modeling, abstention logic, robustness checks, and a premium dark console UI.",
        "3. Functional requirements: detect urgency, credential, portal, and defanged URL cues; compare models; maintain explainability; avoid live fetches.",
        "4. Non-functional requirements: synthetic-only data, compliance-safe banner, no real PII, safe storage of defanged URLs, reproducible training pipeline.",
        "5. Acceptance criteria: AT-01, AT-02, and AT-03 demonstrate legitimate low risk, suspicious phishing escalation, and stable perturbation behavior.",
    ]
    final_sections = [
        "PhishShift Final Report",
        "",
        "Summary: The project builds a synthetic phishing-risk scanner that explains risky message cues, compares three model variants, and preserves a human-in-the-loop helpdesk workflow.",
        "Methodology: Data generation and sanitization ensure no live URLs or secrets are introduced. The corpus is cleaned, deduplicated, split by campaign group, and used for transparent as well as TF-IDF model comparison.",
        "Results: The rules model is explainable, the TF-IDF Logistic Regression model is strongest on the synthetic corpus, and the third model provides a comparison baseline.",
        "Robustness and abstention: Narrow uncertainty bands trigger abstention while benign perturbations remain stable and require analyst review.",
        "Deployment: Render configuration and health checks support a secure, web-based dashboard while keeping the environment isolated from live message traffic.",
    ]
    build_pdf(OUT_DIR / "PhishShift_SRS.pdf", "PhishShift SRS", srs_sections)
    build_pdf(OUT_DIR / "PhishShift_Final_Report.pdf", "PhishShift Final Report", final_sections)
    print("Generated SRS and final report PDFs in reports/")


if __name__ == "__main__":
    main()
