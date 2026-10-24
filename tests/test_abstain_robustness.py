from __future__ import annotations

import json
from pathlib import Path

from app import create_app

ROOT = Path(__file__).resolve().parents[1]
ABSTAIN_PATH = ROOT / "reports" / "abstain_analysis.json"
ROBUST_PATH = ROOT / "reports" / "robustness_drift.json"


def test_abstain_analysis_exists():
    assert ABSTAIN_PATH.exists(), "Abstain analysis JSON should exist"
    data = json.loads(ABSTAIN_PATH.read_text(encoding="utf-8"))
    assert "abstain_rate" in data
    assert "coverage_rate" in data


def test_robustness_analysis_exists():
    assert ROBUST_PATH.exists(), "Robustness drift JSON should exist"
    data = json.loads(ROBUST_PATH.read_text(encoding="utf-8"))
    assert "average_score" in data
    assert "perturbations" in data


def test_robustness_endpoint_returns_different_shifts_by_perturbation():
    app = create_app()
    client = app.test_client()
    payload = {"message": "Urgent action required: verify your password before the account is suspended."}
    response = client.post("/api/robustness", json=payload)
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    results = data["results"]
    assert len(results) >= 6, "Expected six perturbations in the drift report."
    shifts = {row["perturbation"]: row["shift"]["tfidf_lr"] for row in results}
    assert len(set(round(value, 6) for value in shifts.values())) > 1, "Perturbation shifts should vary by transformation."
    base = results[0]["baseline"]["tfidf_lr"]
    assert isinstance(base, (int, float))
