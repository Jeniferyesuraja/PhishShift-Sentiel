from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "processed" / "clean.csv"
OUT_PATH = ROOT / "data" / "processed" / "splits.json"


def make_grouped_splits(df: pd.DataFrame) -> dict:
    groups = df["campaign_group"].dropna().unique().tolist()
    legitimate_groups = [g for g in groups if df.loc[df["campaign_group"] == g, "label"].iloc[0] == "legitimate"]
    test_groups = [g for g in groups if g not in legitimate_groups[:1]]
    if len(test_groups) < 3:
        test_groups = groups[:3]
    train_groups = [g for g in groups if g not in test_groups]
    train_idx = df.index[df["campaign_group"].isin(train_groups)].tolist()
    test_idx = df.index[df["campaign_group"].isin(test_groups)].tolist()
    val_idx = train_idx[: max(1, len(train_idx) // 5)]
    train_idx = [idx for idx in train_idx if idx not in val_idx]
    random_split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_random, test_random = next(random_split.split(df, groups=df["campaign_group"]))
    return {
        "campaign_groups": groups,
        "train_campaigns": sorted(train_groups),
        "val_campaigns": sorted(list(df.iloc[val_idx]["campaign_group"].unique())),
        "test_campaigns": sorted(test_groups),
        "train_ids": [int(idx) for idx in train_idx],
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
