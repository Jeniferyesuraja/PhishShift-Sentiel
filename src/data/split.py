from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "processed" / "clean.csv"
OUT_PATH = ROOT / "data" / "processed" / "splits.json"


def make_grouped_splits(df: pd.DataFrame) -> dict:
    groups = df["campaign_group"].dropna().unique().tolist()
    group_label = df.groupby("campaign_group")["label"].first().to_dict()
    legitimate_groups = [g for g in groups if group_label.get(g) == "legitimate"]
    phishing_groups = [g for g in groups if group_label.get(g) == "phishing"]

    if len(legitimate_groups) >= 2:
        test_groups = [legitimate_groups[-1], phishing_groups[-1]]
    else:
        test_groups = [groups[-1]]

    remaining_groups = [g for g in groups if g not in test_groups]
    if len(remaining_groups) >= 2:
        val_groups = [remaining_groups[0]]
    else:
        val_groups = remaining_groups[:1]
    train_groups = [g for g in groups if g not in test_groups and g not in val_groups]

    original_train_idx = df.index[df["campaign_group"].isin(train_groups)].tolist()
    val_idx = df.index[df["campaign_group"].isin(val_groups)].tolist()
    test_idx = df.index[df["campaign_group"].isin(test_groups)].tolist()

    random_split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_random, test_random = next(random_split.split(df, groups=df["campaign_group"]))

    return {
        "campaign_groups": sorted(groups),
        "train_campaigns": sorted(train_groups),
        "val_campaigns": sorted(val_groups),
        "test_campaigns": sorted(test_groups),
        "train_ids": [int(idx) for idx in original_train_idx],
        "val_ids": [int(idx) for idx in val_idx],
        "test_ids": [int(idx) for idx in test_idx],
        "random_train_ids": [int(i) for i in train_random],
        "random_test_ids": [int(i) for i in test_random],
    }


def main() -> None:
    df = pd.read_csv(INPUT_PATH)
    split_data = make_grouped_splits(df)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(split_data, indent=2), encoding="utf-8")
    print(f"Saved splits to {OUT_PATH}")


if __name__ == "__main__":
    main()
