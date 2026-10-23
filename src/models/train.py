from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from src.models.third_model import build_model as build_third_model
from src.models.tfidf_lr import build_model as build_tfidf_model

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean.csv"
MODEL_OUT = ROOT / "models" / "phishshift_v1.joblib"
METRICS_OUT = ROOT / "metrics.json"
MODEL_CARD = ROOT / "models" / "model_card.md"


def load_split_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df = df.fillna("")
    df["text"] = (df["subject_or_title"].fillna("") + " " + df["body_text"].fillna("")).astype(str)
    return df


def train_models() -> dict:
    df = load_split_data()
    phishing_groups = ["fake_invoice", "parcel_fee", "mfa_fatigue", "ceo_gift_card", "payroll_update", "storage_full", "shortened_prize", "hr_policy", "vpn_expiry", "qr_sms_smish"]
    legitimate_groups = [g for g in df["campaign_group"].unique() if g not in phishing_groups]
    train_groups = phishing_groups[:8] + legitimate_groups[:3]
    test_groups = [g for g in df["campaign_group"].unique() if g not in train_groups]
    train_df = df[df["campaign_group"].isin(train_groups)].copy()
    test_df = df[df["campaign_group"].isin(test_groups)].copy()

    lr_model = build_tfidf_model()
    lr_model.fit(train_df["text"].tolist(), train_df["label"].tolist())
    pred = lr_model.predict(test_df["text"].tolist())
    metrics = {
        "accuracy": float(accuracy_score(test_df["label"], pred)),
        "precision": float(precision_score(test_df["label"], pred, pos_label="phishing", zero_division=0)),
        "recall": float(recall_score(test_df["label"], pred, pos_label="phishing", zero_division=0)),
        "f1": float(f1_score(test_df["label"], pred, pos_label="phishing", zero_division=0)),
    }

    model = {
        "lr": lr_model,
        "third": build_third_model(),
        "rules": "transparent_rule_model",
    }
    model["third"].fit(train_df["text"].tolist(), train_df["label"].tolist())
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_OUT)
    METRICS_OUT.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    MODEL_CARD.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CARD.write_text(
        "# Model card\n\n- Intended use: helpdesk triage for synthetic phishing risk review.\n- Data: locally authored synthetic corpus.\n- Limits: not a guarantee of safety; not for live URL analysis.\n- Ethics: educational and defensive use only.\n",
        encoding="utf-8",
    )
    return metrics


if __name__ == "__main__":
    print(train_models())
