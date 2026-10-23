from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "cp5_demo.json"


def test_cp5_demo_report_exists_and_has_expected_fields():
    assert REPORT_PATH.exists(), "CP-5 demo JSON should exist"
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert payload["scenario"] == "CP-5 demo"
    assert "PHISHING-LIKELY" in payload["expected_verdict"]
    assert "Decision support only - not a guarantee of safety." in payload["decision_support"]
