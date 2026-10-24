from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "processed" / "clean.csv"
OUT_PATH = ROOT / "data" / "processed" / "splits.json"


def make_grouped_splits(df: pd.DataFrame) -> dict:
    groups = df["campaign_group"].dropna().unique().tolist()
    group_label = df.groupby("campaign_group")["label"].first().to_dict()
    phishing_groups = [g for g in groups if group_label.get(g) == "phishing"]
    legitimate_groups = [g for g in groups if group_label.get(g) == "legitimate"]
    test_campaigns = [phishing_groups[-1], legitimate_groups[-1], legitimate_groups[-2]]
    train_campaigns = [g for g in groups if g not in test_campaigns]
    val_campaigns = [train_campaigns[-1]]
    train_campaigns = [g for g in train_campaigns if g not in val_campaigns]

    train_ids = df.index[df["campaign_group"].isin(train_campaigns)].tolist()
    val_ids = df.index[df["campaign_group"].isin(val_campaigns)].tolist()
    test_ids = df.index[df["campaign_group"].isin(test_campaigns)].tolist()

    return {
        "campaign_groups": sorted(groups),
        "train_campaigns": sorted(train_campaigns),
        "val_campaigns": sorted(val_campaigns),
        "test_campaigns": sorted(test_campaigns),
        "train_ids": [int(idx) for idx in train_ids],
        "val_ids": [int(idx) for idx in val_ids],
        "test_ids": [int(idx) for idx in test_ids],
    }


def main() -> None:
    df = pd.read_csv(INPUT_PATH)
    split_data = make_grouped_splits(df)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(split_data, indent=2), encoding="utf-8")
    print(f"Saved splits to {OUT_PATH}")


if __name__ == "__main__":
    main()
