from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "acceptance"
AT_FILES = [
    REPORT_DIR / "AT-01.md",
    REPORT_DIR / "AT-02.md",
    REPORT_DIR / "AT-03.md",
]


def test_acceptance_reports_exist():
    for path in AT_FILES:
        assert path.exists(), f"Missing required acceptance report: {path.name}"


def test_at_01_02_03_content_mentions_expected_outcome():
    contents = [path.read_text(encoding="utf-8") for path in AT_FILES]
    assert "pass" in "\n".join(contents).lower()
    assert "legitimate" in "\n".join(contents).lower() or "phishing" in "\n".join(contents).lower()
