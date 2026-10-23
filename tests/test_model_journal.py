from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "reports" / "model_journal.md"
CSV = ROOT / "reports" / "model_journal.csv"


def test_model_journal_outputs_exist():
    assert JOURNAL.exists(), "Model journal markdown should exist"
    assert CSV.exists(), "Model journal CSV should exist"
    content = JOURNAL.read_text(encoding="utf-8")
    assert "Rules" in content and "TF-IDF LR" in content and "Third model" in content
