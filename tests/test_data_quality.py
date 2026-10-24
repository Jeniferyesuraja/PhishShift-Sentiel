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


def test_metrics_are_not_perfect_and_holdout_is_realistic():
    metrics = json.loads((ROOT / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["accuracy"] < 0.99, "Grouped holdout metrics should not be perfectly inflated."
    assert metrics["f1"] < 0.99, "F1 should remain realistic under campaign holdout."


def test_model_lab_uses_live_metrics_not_hardcoded_numbers():
    from app import create_app

    app = create_app()
    client = app.test_client()
    html = client.get("/model-lab").get_data(as_text=True)
    metrics = json.loads((ROOT / "metrics.json").read_text(encoding="utf-8"))
    assert "0.96" not in html and "0.04" not in html, "Model Lab page still contains stale hardcoded numbers."
    assert str(metrics["accuracy"]) in html or f"{metrics['accuracy']:.2f}" in html
