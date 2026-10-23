from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean.csv"
REPORT_PATH = ROOT / "reports" / "abstain_analysis.json"


def compute_abstain_metrics() -> dict:
    df = pd.read_csv(DATA_PATH).fillna("")
    text = (df["subject_or_title"] + " " + df["body_text"]).astype(str)
    scores: list[float] = []
    for entry in text:
        lowered = entry.lower()
        score = 0.0
        for kw in ["verify", "urgent", "password", "suspended", "portal", "security", "reward", "claim", "click", "before"]:
            if kw in lowered:
                score += 10
        scores.append(min(score, 100.0))

    certainty_threshold = 70
    high_conf = sum(1 for v in scores if v >= certainty_threshold)
    abstain = sum(1 for v in scores if 35 <= v < 65)
    covered = sum(1 for v in scores if v < 35 or v >= 65)
    result = {
        "total_messages": int(len(df)),
        "high_confidence_count": int(high_conf),
        "abstain_count": int(abstain),
        "covered_count": int(covered),
        "abstain_rate": round(abstain / max(1, len(df)), 4),
        "coverage_rate": round(covered / max(1, len(df)), 4),
        "threshold": certainty_threshold,
        "decision_rule": "Abstain when confidence score falls in the uncertain range [35, 65).",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(compute_abstain_metrics())
