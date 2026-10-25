from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = ROOT / "metrics.json"
RESULTS_CSV = ROOT / "reports" / "results_table.csv"


def main() -> None:
    if not METRICS_PATH.exists():
        print("metrics.json not found. Run python -m src.models.train to generate the canonical evaluation artifact.")
        return

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    rows = []
    for model_name, payload in metrics.get("grouped_holdout", {}).items():
        rows.append({
            "model": model_name,
            "accuracy": payload.get("accuracy", 0.0),
            "precision": payload.get("precision", 0.0),
            "recall": payload.get("recall", 0.0),
            "f1": payload.get("f1", 0.0),
            "roc_auc": payload.get("roc_auc", 0.0),
            "pr_auc": payload.get("pr_auc", 0.0),
            "false_positive_rate": payload.get("false_positive_rate", 0.0),
            "coverage_at_abstain": payload.get("coverage_at_abstain", 0.0),
        })

    if not rows:
        rows = [{
            "model": "n/a",
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "roc_auc": 0.0,
            "pr_auc": 0.0,
            "false_positive_rate": 0.0,
            "coverage_at_abstain": 0.0,
        }]

    table = pd.DataFrame(rows)
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(RESULTS_CSV, index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
