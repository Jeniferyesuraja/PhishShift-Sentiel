from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from src.data.dedup import compute_near_duplicates
from src.models.rules import score_message
from src.models.third_model import build_model as build_third_model
from src.models.tfidf_lr import build_model as build_tfidf_model

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean.csv"
MODEL_OUT = ROOT / "models" / "phishshift_v1.joblib"
METRICS_OUT = ROOT / "metrics.json"
RESULTS_CSV = ROOT / "reports" / "results_table.csv"
LOCO_CSV = ROOT / "reports" / "loco.csv"
JOURNAL_PATH = ROOT / "experiments" / "journal.csv"
MODEL_CARD = ROOT / "models" / "model_card.md"


def _probability_of_phishing(model, texts: list[str]) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(texts)
        if hasattr(model, "classes_") and "phishing" in model.classes_:
            idx = list(model.classes_).index("phishing")
            return np.asarray(probs[:, idx], dtype=float)
        if probs.shape[1] == 2:
            return np.asarray(probs[:, 1], dtype=float)
        return np.asarray(probs.max(axis=1), dtype=float)
    scores = model.decision_function(texts)
    if hasattr(scores, "shape") and len(scores.shape) > 1:
        if scores.shape[1] == 2:
            return 1.0 / (1.0 + np.exp(-scores[:, 1]))
        scores = scores[:, 0]
    return 1.0 / (1.0 + np.exp(-np.asarray(scores, dtype=float)))


def _safe_coverage_metrics(y_true: list[str], y_pred: list[str], y_prob: list[float] | None = None) -> dict:
    valid = [idx for idx, pred in enumerate(y_pred) if pred != "abstain"]
    if not valid:
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "coverage": 0.0,
            "roc_auc": 0.0,
            "pr_auc": 0.0,
            "false_positive_rate": 0.0,
            "confusion_matrix": [[0, 0], [0, 0]],
            "covered_accuracy": 0.0,
        }

    y_true_valid = [y_true[i] for i in valid]
    y_pred_valid = [y_pred[i] for i in valid]
    covered_accuracy = round(float(accuracy_score(y_true_valid, y_pred_valid)), 4)
    precision = precision_score(y_true_valid, y_pred_valid, pos_label="phishing", zero_division=0)
    recall = recall_score(y_true_valid, y_pred_valid, pos_label="phishing", zero_division=0)
    f1 = f1_score(y_true_valid, y_pred_valid, pos_label="phishing", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true_valid, y_pred_valid, labels=["legitimate", "phishing"]).ravel()
    fpr = fp / max(1, fp + tn)
    roc_auc = 0.5
    pr_auc = 0.5
    if y_prob is not None and len(valid) > 1:
        prob_valid = [y_prob[i] for i in valid]
        label_bits = [1 if label == "phishing" else 0 for label in y_true_valid]
        if len(set(label_bits)) > 1:
            roc_auc = float(roc_auc_score(label_bits, prob_valid))
            pr_auc = float(average_precision_score(label_bits, prob_valid))
    return {
        "accuracy": round(float(sum(1 for idx, pred in enumerate(y_pred) if pred != "abstain" and y_true[idx] == pred) / max(1, len(y_true))), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "coverage": round(float(len(valid) / len(y_true)), 4),
        "roc_auc": round(float(roc_auc), 4),
        "pr_auc": round(float(pr_auc), 4),
        "false_positive_rate": round(float(fpr), 4),
        "confusion_matrix": confusion_matrix(y_true_valid, y_pred_valid, labels=["legitimate", "phishing"]).tolist(),
        "covered_accuracy": round(float(covered_accuracy), 4),
    }


def rules_predict(texts: list[str], sender_types: list[str], urls: list[str]) -> list[str]:
    preds: list[str] = []
    for idx, text in enumerate(texts):
        score, _ = score_message(text, sender_domain_type=sender_types[idx], url_summary={"has_shortener": "short" in urls[idx].lower(), "lookalike_score": 0.5})
        if score >= 0.62:
            preds.append("phishing")
        elif score <= 0.38:
            preds.append("legitimate")
        else:
            preds.append("abstain")
    return preds


def compute_grouped_holdout(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    campaigns = df["campaign_group"].dropna().unique().tolist()
    group_label = df.groupby("campaign_group")["label"].first().to_dict()
    phishing_groups = [g for g in campaigns if group_label.get(g) == "phishing"]
    legitimate_groups = [g for g in campaigns if group_label.get(g) == "legitimate"]
    holdout = [phishing_groups[-1], legitimate_groups[-1], legitimate_groups[-2]]
    train = [g for g in campaigns if g not in holdout]
    return df[df["campaign_group"].isin(train)].copy(), df[df["campaign_group"].isin(holdout)].copy(), holdout


def compute_random_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_df, test_df = train_test_split(df, test_size=0.2, stratify=df["label"], random_state=42)
    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)


def compute_loco(df: pd.DataFrame, model_name: str, model) -> dict:
    records = []
    campaign_scores = []
    for campaign in df["campaign_group"].dropna().unique().tolist():
        holdout_df = df[df["campaign_group"] == campaign].copy()
        train_df = df[df["campaign_group"] != campaign].copy()
        if model_name == "rules":
            preds = pd.Series(rules_predict(holdout_df["text"].tolist(), holdout_df["sender_domain_type"].tolist(), holdout_df["url_text"].tolist())).reset_index(drop=True)
        else:
            if model_name == "tfidf_lr":
                fitted = build_tfidf_model()
            else:
                fitted = build_third_model()
            fitted.fit(train_df["text"].tolist(), train_df["label"].tolist())
            probs = _probability_of_phishing(fitted, holdout_df["text"].tolist())
            preds = pd.Series(np.where(probs >= 0.5, "phishing", "legitimate")).reset_index(drop=True)

        valid_mask = preds.ne("abstain").to_numpy()
        valid_true = holdout_df["label"].reset_index(drop=True)[valid_mask]
        valid_pred = preds[valid_mask].reset_index(drop=True)
        if len(valid_pred) == 0:
            score = 0.0
            f1 = 0.0
        else:
            score = float(accuracy_score(valid_true, valid_pred))
            f1 = float(f1_score(valid_true, valid_pred, pos_label="phishing", zero_division=0))
        cal = {"campaign_group": campaign, "accuracy": round(score, 4), "f1": round(f1, 4)}
        records.append(cal)
        campaign_scores.append(cal["accuracy"])

    if len(campaign_scores) > 1:
        mean_acc = round(float(np.mean(campaign_scores)), 4)
        std_acc = round(float(np.std(campaign_scores, ddof=1)), 4)
    else:
        mean_acc = round(float(np.mean(campaign_scores)), 4) if campaign_scores else 0.0
        std_acc = 0.0
    return {"mean_accuracy": mean_acc, "std_accuracy": std_acc, "campaign_scores": records}


def write_results_table(results: dict) -> None:
    rows = []
    for model_name, metrics in results.items():
        rows.append(
            {
                "model": model_name,
                "accuracy": metrics.get("accuracy", 0.0),
                "precision": metrics.get("precision", 0.0),
                "recall": metrics.get("recall", 0.0),
                "f1": metrics.get("f1", 0.0),
                "roc_auc": metrics.get("roc_auc", 0.0),
                "pr_auc": metrics.get("pr_auc", 0.0),
                "false_positive_rate": metrics.get("false_positive_rate", 0.0),
                "coverage_at_abstain": metrics.get("coverage_at_abstain", 0.0),
                "loco_mean_accuracy": metrics.get("loco_mean_accuracy", 0.0),
                "loco_std_accuracy": metrics.get("loco_std_accuracy", 0.0),
            }
        )
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(RESULTS_CSV, index=False)


def write_loco_csv(loco_by_model: dict) -> None:
    rows = []
    for model_name, payload in loco_by_model.items():
        for campaign in payload.get("campaign_scores", []):
            rows.append({"model": model_name, "campaign_group": campaign["campaign_group"], "accuracy": campaign["accuracy"], "f1": campaign.get("f1", campaign["accuracy"])})
    LOCO_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(LOCO_CSV, index=False)


def write_journal(metrics: dict) -> None:
    rows = []
    for split_name, split_info in metrics.get("grouped_holdout", {}).items():
        rows.append({"split": "grouped_holdout", "model": split_name, **split_info})
    for split_name, split_info in metrics.get("random_split", {}).items():
        rows.append({"split": "random_split", "model": split_name, **split_info})
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(JOURNAL_PATH, index=False)


def train_models() -> dict:
    df = pd.read_csv(DATA_PATH).fillna("")
    df["text"] = (df["subject_or_title"].fillna("") + " " + df["body_text"].fillna("")).astype(str)
    df["url_text"] = df["sanitized_url_features"].fillna("{}")
    dedup_df, _ = compute_near_duplicates(df, threshold=0.90)
    train_df, test_df, holdout_campaigns = compute_grouped_holdout(dedup_df)

    model_map = {"rules": None, "tfidf_lr": build_tfidf_model(), "third_model": build_third_model()}
    grouped_results = {}
    loco_by_model = {}

    for model_name, model in model_map.items():
        if model_name == "rules":
            y_true = test_df["label"].tolist()
            y_pred = rules_predict(test_df["text"].tolist(), test_df["sender_domain_type"].tolist(), test_df["url_text"].tolist())
            rule_probs = [max(0.0, min(1.0, score_message(text, sender_domain_type=sender_type, url_summary={"has_shortener": "short" in url.lower(), "lookalike_score": 0.5})[0])) for text, sender_type, url in zip(test_df["text"].tolist(), test_df["sender_domain_type"].tolist(), test_df["url_text"].tolist())]
            metrics = _safe_coverage_metrics(y_true, y_pred, rule_probs)
            grouped_results[model_name] = metrics
            loco_by_model[model_name] = compute_loco(dedup_df.assign(text=dedup_df["text"], url_text=dedup_df["sanitized_url_features"].fillna("{}")), model_name, model)
        else:
            model.fit(train_df["text"].tolist(), train_df["label"].tolist())
            probs = _probability_of_phishing(model, test_df["text"].tolist())
            y_pred = ["phishing" if prob >= 0.5 else "legitimate" for prob in probs]
            metrics = _safe_coverage_metrics(test_df["label"].tolist(), y_pred, probs.tolist())
            grouped_results[model_name] = metrics
            loco_by_model[model_name] = compute_loco(dedup_df.assign(text=dedup_df["text"], url_text=dedup_df["sanitized_url_features"].fillna("{}")), model_name, model)

    for model_name, metrics in grouped_results.items():
        metrics["coverage_at_abstain"] = metrics.get("coverage", 0.0)
        metrics["false_positive_rate"] = metrics.get("false_positive_rate", 0.0)
        loco = loco_by_model.get(model_name, {})
        metrics["loco_mean_accuracy"] = loco.get("mean_accuracy", 0.0)
        metrics["loco_std_accuracy"] = loco.get("std_accuracy", 0.0)

    random_train, random_test = compute_random_split(dedup_df)
    random_results = {}
    for model_name, model in model_map.items():
        if model_name == "rules":
            y_true = random_test["label"].tolist()
            y_pred = rules_predict(random_test["text"].tolist(), random_test["sender_domain_type"].tolist(), random_test["url_text"].tolist())
            random_results[model_name] = _safe_coverage_metrics(y_true, y_pred, [max(0.0, min(1.0, score_message(t, sender_domain_type=s, url_summary={"has_shortener": "short" in u.lower(), "lookalike_score": 0.5})[0])) for t, s, u in zip(random_test["text"].tolist(), random_test["sender_domain_type"].tolist(), random_test["url_text"].tolist())])
        else:
            model.fit(random_train["text"].tolist(), random_train["label"].tolist())
            probs = _probability_of_phishing(model, random_test["text"].tolist())
            y_pred = ["phishing" if prob >= 0.5 else "legitimate" for prob in probs]
            random_results[model_name] = _safe_coverage_metrics(random_test["label"].tolist(), y_pred, probs.tolist())

    metrics = {
        "dataset_rows": len(dedup_df),
        "campaigns": int(dedup_df["campaign_group"].nunique()),
        "holdout_campaigns": holdout_campaigns,
        "grouped_holdout": grouped_results,
        "random_split": random_results,
        "loco": {model_name: {"mean_accuracy": rec.get("loco_mean_accuracy", 0.0), "std_accuracy": rec.get("loco_std_accuracy", 0.0), "campaign_scores": rec.get("campaign_scores", [])} for model_name, rec in loco_by_model.items()},
        "leakage_gap": {
            "accuracy_gap": round(float(random_results["tfidf_lr"]["accuracy"] - grouped_results["tfidf_lr"]["accuracy"]), 4),
            "f1_gap": round(float(random_results["tfidf_lr"]["f1"] - grouped_results["tfidf_lr"]["f1"]), 4),
        },
        "accuracy": grouped_results["tfidf_lr"]["accuracy"],
        "precision": grouped_results["tfidf_lr"]["precision"],
        "recall": grouped_results["tfidf_lr"]["recall"],
        "f1": grouped_results["tfidf_lr"]["f1"],
        "roc_auc": grouped_results["tfidf_lr"]["roc_auc"],
        "pr_auc": grouped_results["tfidf_lr"]["pr_auc"],
        "false_positive_rate": grouped_results["tfidf_lr"]["false_positive_rate"],
        "coverage_at_abstain": grouped_results["tfidf_lr"]["coverage_at_abstain"],
    }

    METRICS_OUT.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_results_table(grouped_results)
    write_loco_csv(loco_by_model)
    write_journal(metrics)
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"rules": "transparent_rule_model", "tfidf_lr": model_map["tfidf_lr"], "third_model": model_map["third_model"]}, MODEL_OUT)
    MODEL_CARD.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CARD.write_text("# Model card\n\n- Intended use: helpdesk triage for synthetic phishing risk review.\n- Data: locally authored synthetic corpus.\n- Limits: not a guarantee of safety; not for live URL analysis.\n- Ethics: educational and defensive use only.\n", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train_models(), indent=2))
