from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean.csv"
RESULTS_MD = ROOT / "reports" / "results_table.md"
RESULTS_CSV = ROOT / "reports" / "results_table.csv"


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    preds = ["phishing" if "verify" in row["body_text"].lower() or "urgent" in row["body_text"].lower() else "legitimate" for _, row in df.iterrows()]
    labels = df["label"].tolist()
    acc = accuracy_score(labels, preds)
    precision = precision_score(labels, preds, pos_label="phishing", zero_division=0)
    recall = recall_score(labels, preds, pos_label="phishing", zero_division=0)
    f1 = f1_score(labels, preds, pos_label="phishing", zero_division=0)
    cm = confusion_matrix(labels, preds, labels=["legitimate", "phishing"])
    table = pd.DataFrame(
        [{
            "model": "rules",
            "accuracy": acc,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "confusion_matrix": str(cm.tolist()),
        }]
    )
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(RESULTS_CSV, index=False)
    RESULTS_MD.write_text(
        "# Results summary\n\n| model | accuracy | precision | recall | f1 |\n| --- | ---: | ---: | ---: | ---: |\n| rules | " + f"{acc:.3f} | {precision:.3f} | {recall:.3f} | {f1:.3f} |\n",
        encoding="utf-8",
    )
    print(table.to_dict(orient="records"))


if __name__ == "__main__":
    main()
