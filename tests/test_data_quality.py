from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = ROOT / "data" / "processed" / "clean.csv"
SPLIT_PATH = ROOT / "data" / "processed" / "splits.json"
DEDUP_AUDIT = ROOT / "reports" / "dedup_audit.csv"
DEDUP_PROOF = ROOT / "docs" / "dedup_proof.md"


def test_clean_data_has_unique_message_ids_and_labels():
    df = pd.read_csv(CLEAN_PATH)
    assert not df.empty
    assert df["message_id"].is_unique
    assert set(df["label"].unique()) == {"legitimate", "phishing"}
    assert df["campaign_group"].notna().all()


def test_grouped_split_is_disjoint_and_has_documents():
    assert SPLIT_PATH.exists(), "splits.json should exist after running split generation"
    split_data = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    train = set(split_data["train_campaigns"])
    val = set(split_data["val_campaigns"])
    test = set(split_data["test_campaigns"])
    assert train.isdisjoint(test)
    assert val.isdisjoint(test)
    assert train
    assert test


def test_dedup_audit_outputs_exist():
    assert DEDUP_AUDIT.exists(), "dedup audit CSV should exist"
    assert DEDUP_PROOF.exists(), "dedup proof markdown should exist"
    audit = pd.read_csv(DEDUP_AUDIT)
    assert "message_a" in audit.columns and "message_b" in audit.columns
