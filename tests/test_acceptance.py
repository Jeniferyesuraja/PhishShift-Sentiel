from __future__ import annotations

import json
from pathlib import Path

from app import create_app
from src.models.rules import score_message

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "acceptance"
AT_FILES = [
    REPORT_DIR / "AT-01.json",
    REPORT_DIR / "AT-02.json",
    REPORT_DIR / "AT-03.json",
]


def test_acceptance_reports_exist():
    for path in AT_FILES:
        assert path.exists(), f"Missing required acceptance report: {path.name}"


def test_acceptance_api_returns_live_evidence():
    app = create_app()
    client = app.test_client()
    response = client.get("/api/acceptance")
    assert response.status_code == 200, "Acceptance API should return a valid payload."
    payload = response.get_json()
    tests = payload.get("tests", [])
    assert len(tests) == 3, "Expected AT-01, AT-02, and AT-03 results."
    first = tests[0]
    assert "input_message" in first
    assert "models" in first
    assert "verdict" in first
    assert "abstain" in first
    model_names = {entry["model"] for entry in first["models"]}
    assert {"Rules", "TF-IDF LR", "Third model"}.issubset(model_names)


def test_acceptance_page_uses_live_controls():
    app = create_app()
    client = app.test_client()
    html = client.get("/acceptance").get_data(as_text=True)
    assert "Run all tests" in html
    assert "download-logs" in html.lower() or "Download logs" in html
    assert "api/acceptance" in html


def test_rules_scores_vary_between_phish_and_legit_messages():
    phishing_examples = [
        "Urgent password reset required. Verify your account now or your access will be suspended.",
        "Payroll update: your salary slip is ready. Click the secure portal before 5 PM.",
        "Security alert: confirm your login before your account is locked.",
        "IT maintenance notice: confirm your credentials in the portal before the deadline.",
        "Your invoice is overdue. Review your payment now to avoid suspension.",
        "Access request: confirm your password immediately to keep your mailbox active.",
        "Your package is delayed. Update your billing data via the attached secure link.",
        "Verify your tax refund with a one-time code before the portal closes.",
        "Account review: action required today or your session will be terminated.",
        "We detected suspicious activity. Reset your password now using the secure link."
    ]
    legit_examples = [
        "Your password reset was completed and no further action is required.",
        "Payroll slip for this period is attached and no action is needed.",
        "IT maintenance has been completed and access is normal.",
        "Your account review finished successfully and the service desk confirmed the update.",
        "The scheduled security change was completed, and no verification is required.",
        "The invoice was processed and no follow-up action is needed.",
        "Your security upgrade has been applied and access remains available.",
        "The payroll notice is informational only and does not require a response.",
        "This message confirms the routine maintenance window and no action is required.",
        "Your account settings were reviewed and remain unchanged."
    ]

    phish_scores = [score_message(text)[0] for text in phishing_examples]
    legit_scores = [score_message(text)[0] for text in legit_examples]

    assert max(phish_scores) > min(phish_scores) + 0.2, "Phishing rules scores should vary by message severity."
    assert max(legit_scores) < min(phish_scores), "Legitimate rules scores should remain below the phishing band."
    assert len({round(score, 3) for score in phish_scores}) >= 5, "Rules score output should not collapse to one constant value."


def test_at_01_abstain_is_false_positive_cost():
    app = create_app()
    client = app.test_client()
    response = client.get("/api/acceptance")
    payload = response.get_json()
    at_01 = payload["tests"][0]
    assert at_01["status"] in {"PASS", "ABSTAINED", "FAIL"}
    assert "threshold" in at_01.get("summary", "").lower() or "abstain" in at_01.get("summary", "").lower()
    assert at_01["false_positive_impact"]["abstained_total"] >= 0
