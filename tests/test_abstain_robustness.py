from __future__ import annotations

import json
from pathlib import Path

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
