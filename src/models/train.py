from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
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
JOURNAL_PATH = ROOT / "experiments" / "journal.csv"
MODEL_CARD = ROOT / "models" / "model_card.md"


def safe_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    valid = [idx for idx, pred in enumerate(y_pred) if pred != "abstain"]
    if not valid:
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "coverage": 0.0,
        }
    y_true_valid = [y_true[i] for i in valid]
    y_pred_valid = [y_pred[i] for i in valid]
    covered_accuracy = round(float(accuracy_score(y_true_valid, y_pred_valid)), 4)
    overall_accuracy = round(float(sum(1 for idx, pred in enumerate(y_pred) if pred != "abstain" and y_true[idx] == pred) / max(1, len(y_true))), 4)
    return {
        "accuracy": overall_accuracy,
        "precision": round(float(precision_score(y_true_valid, y_pred_valid, pos_label="phishing", zero_division=0)), 4),
        "recall": round(float(recall_score(y_true_valid, y_pred_valid, pos_label="phishing", zero_division=0)), 4),
        "f1": round(float(f1_score(y_true_valid, y_pred_valid, pos_label="phishing", zero_division=0)), 4),
        "coverage": round(float(len(valid) / len(y_true)), 4),
        "covered_accuracy": covered_accuracy,
    }


def rules_predict(texts: list[str], sender_types: list[str], urls: list[str]) -> list[str]:
    preds: list[str] = []
    for idx, text in enumerate(texts):
        score, _ = score_message(text, sender_domain_type=sender_types[idx], url_summary={"has_shortener": "short" in urls[idx].lower(), "lookalike_score": 0.5})
        if score < 0.45:
            preds.append("abstain")
        else:
            preds.append("phishing" if score >= 0.55 else "legitimate")
    return preds


def compute_grouped_holdout(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    campaigns = df["campaign_group"].dropna().unique().tolist()
    phishing_groups = [g for g in campaigns if df.loc[df["campaign_group"] == g, "label"].iloc[0] == "phishing"]
    legitimate_groups = [g for g in campaigns if df.loc[df["campaign_group"] == g, "label"].iloc[0] == "legitimate"]
    holdout = [phishing_groups[-1], legitimate_groups[-1], legitimate_groups[-2]]
    train = [g for g in campaigns if g not in holdout]
    return df[df["campaign_group"].isin(train)].copy(), df[df["campaign_group"].isin(holdout)].copy(), holdout


def compute_random_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_df, test_df = train_test_split(df, test_size=0.2, stratify=df["label"], random_state=42)
    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)


def compute_loco_metrics(df: pd.DataFrame) -> dict:
    campaign_scores = []
    for campaign in df["campaign_group"].unique():
        test_df = df[df["campaign_group"] == campaign].copy()
        train_df = df[df["campaign_group"] != campaign].copy()
        model = build_tfidf_model()
        model.fit(train_df["text"].tolist(), train_df["label"].tolist())
        preds = model.predict(test_df["text"].tolist())
        campaign_scores.append(float((preds == test_df["label"].tolist()).mean()))
    return {"mean_accuracy": round(float(sum(campaign_scores) / len(campaign_scores)), 4), "std_accuracy": round(float(pd.Series(campaign_scores).std(ddof=1)), 4)}


def write_results_table(results: dict) -> None:
    table = []
    for model_name, metrics in results.items():
        table.append({
            "model": model_name,
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "false_positive_rate": metrics.get("false_positive_rate", 0.0),
            "coverage_at_abstain": metrics.get("coverage_at_abstain", 1.0),
            "loco_mean_f1": metrics.get("loco_mean_f1", 0.0),
            "loco_std_f1": metrics.get("loco_std_f1", 0.0),
        })
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(table).to_csv(RESULTS_CSV, index=False)


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

    model_map = {
        "rules": None,
        "tfidf_lr": build_tfidf_model(),
        "third_model": build_third_model(),
    }

    grouped_results = {}
    for model_name, model in model_map.items():
        if model_name == "rules":
            y_true = test_df["label"].tolist()
            y_pred = rules_predict(test_df["text"].tolist(), test_df["sender_domain_type"].tolist(), test_df["url_text"].tolist())
            metrics = safe_metrics(y_true, y_pred)
            tn = sum(1 for actual, pred in zip(y_true, y_pred) if actual == "legitimate" and pred == "legitimate")
            fp = sum(1 for actual, pred in zip(y_true, y_pred) if actual == "legitimate" and pred == "phishing")
            metrics["false_positive_rate"] = round(float(fp / max(1, fp + tn)), 4)
            metrics["coverage_at_abstain"] = metrics.get("coverage", 0.0)
            metrics["loco_mean_f1"] = 0.0
            metrics["loco_std_f1"] = 0.0
            grouped_results[model_name] = metrics
        else:
            model.fit(train_df["text"].tolist(), train_df["label"].tolist())
            proba = model.predict_proba(test_df["text"].tolist()) if hasattr(model, "predict_proba") else None
            if proba is not None:
                confidences = proba.max(axis=1)
                y_pred = []
                for idx, conf in enumerate(confidences):
                    if conf < 0.90:
                        y_pred.append("abstain")
                    else:
                        y_pred.append(model.classes_[proba[idx].argmax()])
            else:
                decisions = model.decision_function(test_df["text"].tolist())
                conf = abs(decisions).max(axis=1) if len(decisions.shape) > 1 else abs(decisions)
                y_pred = []
                for idx, c in enumerate(conf):
                    y_pred.append("abstain" if c < 0.90 else ("phishing" if model.predict(test_df["text"].tolist()[idx:idx + 1])[0] == "phishing" else "legitimate"))
            metrics = safe_metrics(test_df["label"].tolist(), y_pred)
            metrics["false_positive_rate"] = round(float(sum(1 for actual, pred in zip(test_df["label"].tolist(), y_pred) if actual == "legitimate" and pred == "phishing") / max(1, sum(1 for actual in test_df["label"].tolist() if actual == "legitimate"))), 4)
            metrics["coverage_at_abstain"] = metrics.get("coverage", 0.0)
            metrics["loco_mean_f1"] = round(float(compute_loco_metrics(dedup_df)["mean_accuracy"]), 4)
            metrics["loco_std_f1"] = round(float(compute_loco_metrics(dedup_df)["std_accuracy"]), 4)
            grouped_results[model_name] = metrics

    random_train, random_test = compute_random_split(dedup_df)
    random_results = {}
    for model_name, model in model_map.items():
        if model_name == "rules":
            y_true = random_test["label"].tolist()
            y_pred = rules_predict(random_test["text"].tolist(), random_test["sender_domain_type"].tolist(), random_test["url_text"].tolist())
            random_results[model_name] = safe_metrics(y_true, y_pred)
        else:
            model.fit(random_train["text"].tolist(), random_train["label"].tolist())
            y_pred = model.predict(random_test["text"].tolist())
            random_results[model_name] = safe_metrics(random_test["label"].tolist(), y_pred)

    metrics = {
        "dataset_rows": len(dedup_df),
        "campaigns": int(dedup_df["campaign_group"].nunique()),
        "holdout_campaigns": holdout_campaigns,
        "grouped_holdout": grouped_results,
        "random_split": random_results,
        "loco": {"tfidf_lr": compute_loco_metrics(dedup_df)},
        "leakage_gap": {
            "accuracy_gap": round(float(random_results["tfidf_lr"]["accuracy"] - grouped_results["tfidf_lr"]["accuracy"]), 4),
            "f1_gap": round(float(random_results["tfidf_lr"]["f1"] - grouped_results["tfidf_lr"]["f1"]), 4),
        },
        "accuracy": grouped_results["tfidf_lr"]["accuracy"],
        "precision": grouped_results["tfidf_lr"]["precision"],
        "recall": grouped_results["tfidf_lr"]["recall"],
        "f1": grouped_results["tfidf_lr"]["f1"],
        "false_positive_rate": grouped_results["tfidf_lr"]["false_positive_rate"],
        "coverage_at_abstain": grouped_results["tfidf_lr"]["coverage_at_abstain"],
    }

    METRICS_OUT.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_results_table({**grouped_results, "random_split": {**random_results["tfidf_lr"]}})
    write_journal(metrics)
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"rules": "transparent_rule_model", "tfidf_lr": model_map["tfidf_lr"], "third_model": model_map["third_model"]}, MODEL_OUT)
    MODEL_CARD.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CARD.write_text("# Model card\n\n- Intended use: helpdesk triage for synthetic phishing risk review.\n- Data: locally authored synthetic corpus.\n- Limits: not a guarantee of safety; not for live URL analysis.\n- Ethics: educational and defensive use only.\n", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(train_models())
