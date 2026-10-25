from __future__ import annotations

import argparse
import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

from src.models.rules import score_message
from src.models.third_model import build_model as build_third_model
from src.models.tfidf_lr import build_model as build_tfidf_model

DEFAULT_COLUMNS = [
    "message_id",
    "channel",
    "subject_or_title",
    "body_text",
    "sanitized_url_features",
    "sender_domain_type",
    "label",
    "campaign_group",
    "collected_date",
    "source_type",
]
REQUIRED_COLUMNS = [
    "message_id",
    "channel",
    "subject_or_title",
    "body_text",
    "sanitized_url_features",
    "sender_domain_type",
    "campaign_group",
    "collected_date",
    "source_type",
]
VALID_CHANNELS = {"email", "sms", "chat", "voice"}
MAX_FILE_BYTES = 2 * 1024 * 1024


def defang_url(url: str) -> str:
    if not isinstance(url, str):
        return ""
    value = url.strip()
    if not value:
        return value
    value = value.replace("https://", "hxxps://").replace("http://", "hxxp://")
    value = value.replace(".", "[.]")
    return value


def _normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _parse_url_summary(value: Any) -> dict[str, Any]:
    if value is None or pd.isna(value):
        return {"has_shortener": False, "lookalike_score": 0.0}
    if isinstance(value, dict):
        return {
            "has_shortener": bool(value.get("has_shortener")),
            "lookalike_score": float(value.get("lookalike_score", 0.0)),
        }
    text = str(value)
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return _parse_url_summary(payload)
    except Exception:
        pass
    lowered = text.lower()
    return {
        "has_shortener": any(token in lowered for token in ["bit.ly", "tinyurl", "t.co", "ow.ly", "goo.gl", "short"]),
        "lookalike_score": 0.8 if "lookalike" in lowered or "secure" in lowered else 0.15,
    }


def _keywords_for_text(message: str) -> list[str]:
    lowered = message.lower()
    cues: list[str] = []
    if any(token in lowered for token in ["password", "login", "credential", "reset", "verify identity"]):
        cues.append("credential or sensitive account wording")
    if any(token in lowered for token in ["urgent", "final", "immediate", "expire", "verify", "suspended", "today"]):
        cues.append("urgency or deadline pressure")
    if "hxxp" in lowered or "http" in lowered or "link" in lowered or "portal" in lowered:
        cues.append("URL or domain suspicion")
    if not any(token in lowered for token in ["dear", "hello", "thanks"]):
        cues.append("generic greeting absent")
    return cues[:5]


@lru_cache(maxsize=1)
def _project_model_bundle() -> dict[str, Any]:
    data_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "clean.csv"
    if not data_path.exists():
        return {"rules": None, "tfidf_lr": build_tfidf_model(), "third": build_third_model()}

    df = pd.read_csv(data_path).fillna("")
    df["text"] = (df["subject_or_title"].fillna("") + " " + df["body_text"].fillna("")).astype(str).str.strip()

    model_map = {
        "tfidf_lr": build_tfidf_model(),
        "third": build_third_model(),
    }
    for name, model in model_map.items():
        model.fit(df["text"].tolist(), df["label"].tolist())
    return model_map


def _rule_probability(text: str, sender_type: str, url_summary: dict[str, Any]) -> float:
    probability, _ = score_message(text, sender_domain_type=sender_type, url_summary=url_summary)
    return float(probability)


def _tfidf_probability(model_name: str, model: Any, text: str) -> float:
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba([text])[0]
        if hasattr(model, "classes_") and "phishing" in model.classes_:
            index = list(model.classes_).index("phishing")
            return float(probs[index])
        if len(probs) == 2:
            return float(probs[1])
        return float(max(probs))
    if hasattr(model, "decision_function"):
        score = float(model.decision_function([text])[0])
        return float(1.0 / (1.0 + np.exp(-score)))
    prediction = model.predict([text])[0]
    return 1.0 if str(prediction).lower() == "phishing" else 0.0


def _third_probability(model_name: str, model: Any, text: str) -> float:
    return _tfidf_probability(model_name, model, text)


def _probability_by_model(model_name: str, model: Any, text: str, sender_type: str, url_summary: dict[str, Any]) -> float:
    if model_name == "Rules":
        return _rule_probability(text, sender_type, url_summary)
    if model_name == "TF-IDF LR":
        return _tfidf_probability(model_name, model, text)
    return _third_probability(model_name, model, text)


def _verdict_for_probability(model_name: str, probability: float) -> tuple[str, bool]:
    if model_name == "Rules":
        if probability >= 0.62:
            return "PHISHING", False
        if probability <= 0.38:
            return "LEGITIMATE", False
        return "ABSTAIN", True
    if probability >= 0.5:
        return "PHISHING", False
    if probability < 0.5:
        return "LEGITIMATE", False
    return "ABSTAIN", True


def _row_overall_verdict(model_scores: dict[str, dict[str, Any]]) -> str:
    verdicts = [entry["verdict"] for entry in model_scores.values()]
    phishing_count = verdicts.count("PHISHING")
    legitimate_count = verdicts.count("LEGITIMATE")
    if phishing_count >= 2:
        return "PHISHING"
    if legitimate_count >= 2:
        return "LEGITIMATE"
    if phishing_count == 1 and legitimate_count == 0:
        return "PHISHING"
    if legitimate_count == 1 and phishing_count == 0:
        return "LEGITIMATE"
    max_prob = max(float(entry["probability"]) for entry in model_scores.values())
    if max_prob >= 0.62:
        return "PHISHING"
    if max_prob <= 0.38:
        return "LEGITIMATE"
    return "ABSTAIN"


def _compute_label_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    filtered_true: list[str] = []
    filtered_pred: list[str] = []
    for actual, predicted in zip(y_true, y_pred):
        actual_label = str(actual).lower()
        predicted_label = str(predicted).lower()
        if predicted_label == "abstain":
            continue
        filtered_true.append(actual_label)
        filtered_pred.append(predicted_label)
    if not filtered_true:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "false_positive_rate": 0.0, "confusion_matrix": [[0, 0], [0, 0]], "legit_false_positive_rate": 0.0}
    tn, fp, fn, tp = confusion_matrix(filtered_true, filtered_pred, labels=["legitimate", "phishing"]).ravel()
    precision = precision_score(filtered_true, filtered_pred, pos_label="phishing", zero_division=0)
    recall = recall_score(filtered_true, filtered_pred, pos_label="phishing", zero_division=0)
    f1 = f1_score(filtered_true, filtered_pred, pos_label="phishing", zero_division=0)
    legit_total = max(1, (pd.Series(filtered_true) == "legitimate").sum())
    legit_false_positive_rate = fp / legit_total
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "false_positive_rate": float(fp / max(1, fp + tn)),
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "legit_false_positive_rate": float(legit_false_positive_rate),
    }


def _per_campaign_breakdown(df: pd.DataFrame, model_name: str) -> dict[str, Any]:
    breakdown: dict[str, Any] = {}
    for campaign, group in df.groupby("campaign_group", dropna=False):
        campaign_name = "unknown" if pd.isna(campaign) else str(campaign)
        group = group[group["predicted"].astype(str).str.upper() != "ABSTAIN"].copy()
        preds = group["predicted"].astype(str).str.upper()
        labels = group["label"].fillna("").astype(str).str.lower()
        if labels.empty:
            breakdown[campaign_name] = {"rows": int(len(group)), "phishing_flagged": int((preds == "PHISHING").sum())}
            continue
        tp = int(((labels == "phishing") & (preds == "PHISHING")).sum())
        fp = int(((labels == "legitimate") & (preds == "PHISHING")).sum())
        tn = int(((labels == "legitimate") & (preds == "LEGITIMATE")).sum())
        fn = int(((labels == "phishing") & (preds == "LEGITIMATE")).sum())
        legit_total = int((labels == "legitimate").sum())
        breakdown[campaign_name] = {
            "rows": int(len(group)),
            "phishing_flagged": int((preds == "PHISHING").sum()),
            "false_positive_rate": round(float(fp / max(1, legit_total)), 4),
            "confusion_matrix": [[tn, fp], [fn, tp]],
        }
    return breakdown


def validate_and_normalize_csv(path: str | Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    if csv_path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"File exceeds 2 MB limit: {csv_path.name}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Could not read CSV: {exc}") from exc

    errors: list[str] = []
    logs: list[str] = []
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")

    if errors:
        return df, errors, logs

    df = df.copy()
    normalized = df.rename(columns=lambda value: str(value).strip())
    for column in DEFAULT_COLUMNS:
        if column not in normalized.columns:
            continue
        normalized[column] = normalized[column].map(lambda value: _normalize_text(value))

    normalized["channel"] = normalized["channel"].fillna("").astype(str).str.lower()
    invalid_channels = sorted(set(normalized["channel"]) - VALID_CHANNELS)
    if invalid_channels:
        errors.append(f"Bad channel values: {', '.join(invalid_channels)}")

    if normalized["body_text"].fillna("").astype(str).str.strip().eq("").any():
        errors.append("Empty body_text values are not allowed.")

    normalized["body_text"] = normalized["body_text"].map(lambda text: re.sub(r"https?://[^\s]+", lambda match: defang_url(match.group(0)), str(text)))
    normalized["sanitized_url_features"] = normalized["sanitized_url_features"].map(
        lambda value: defang_url(str(value)) if isinstance(value, str) and any(token in value.lower() for token in ["http://", "https://"]) else str(value or "")
    )

    for row_index, row in normalized.iterrows():
        if isinstance(row.get("sanitized_url_features"), str) and any(token in row["sanitized_url_features"].lower() for token in ["http://", "https://"]):
            logs.append(f"Row {row.get('message_id', row_index)}: URL was auto-defanged to remove live URL syntax.")
        row_body = str(row.get("body_text", ""))
        if re.search(r"https?://", row_body):
            logs.append(f"Row {row.get('message_id', row_index)}: non-defanged URL in body_text was auto-defanged.")
            normalized.at[row_index, "body_text"] = re.sub(r"https?://[^\s]+", lambda match: defang_url(match.group(0)), row_body)

    normalized["label"] = normalized["label"].fillna("").str.lower()
    normalized["campaign_group"] = normalized["campaign_group"].fillna("unknown")
    normalized["source_type"] = normalized["source_type"].fillna("mentor")
    normalized["message_id"] = normalized["message_id"].where(normalized["message_id"].notna(), "msg_" + normalized.index.astype(str))

    return normalized, errors, logs


def evaluate_csv(csv_paths: str | Path | Iterable[str | Path]) -> dict[str, Any]:
    if isinstance(csv_paths, (str, Path)):
        sources = [csv_paths]
    else:
        sources = list(csv_paths)

    if not sources:
        raise ValueError("Provide at least one CSV file to evaluate.")

    frames: list[pd.DataFrame] = []
    validation_errors: list[str] = []
    validation_logs: list[str] = []
    for source in sources:
        df, errors, logs = validate_and_normalize_csv(source)
        if errors:
            validation_errors.extend([f"{Path(source).name}: {error}" for error in errors])
            continue
        frames.append(df)
        validation_logs.extend(logs)

    if not frames:
        raise ValueError("No valid CSV rows available. " + "; ".join(validation_errors))

    df = pd.concat(frames, ignore_index=True)
    if "label" in df.columns:
        has_labels = bool(df["label"].fillna("").astype(str).str.strip().ne("").any())
    else:
        has_labels = False

    project_bundle = _project_model_bundle()
    model_names = ["Rules", "TF-IDF LR", "Third"]
    rows: list[dict[str, Any]] = []
    model_results: dict[str, list[str]] = {name: [] for name in model_names}
    model_labels: dict[str, list[str]] = {name: [] for name in model_names}
    if has_labels:
        label_values = df["label"].astype(str).str.lower().fillna("")
    else:
        label_values = pd.Series([""] * len(df), index=df.index)

    for row in df.itertuples(index=False):
        message_id = getattr(row, "message_id", "")
        channel = str(getattr(row, "channel", "email")).lower()
        sender_type = str(getattr(row, "sender_domain_type", "unknown")).lower()
        subject = str(getattr(row, "subject_or_title", "")).strip()
        body = str(getattr(row, "body_text", "")).strip()
        url_value = getattr(row, "sanitized_url_features", "{}")
        url_summary = _parse_url_summary(url_value)
        text = " ".join(part for part in [subject, body] if part).strip()
        if not text:
            continue
        score_map: dict[str, dict[str, Any]] = {}
        for model_name in model_names:
            if model_name == "Rules":
                prob = _rule_probability(text, sender_type, url_summary)
                verdict, abstain = _verdict_for_probability(model_name, prob)
                cues = score_message(text, sender_domain_type=sender_type, url_summary=url_summary)[1][:5]
                score_map[model_name] = {"probability": round(float(prob), 4), "verdict": verdict, "abstain": abstain, "top_cues": cues}
            else:
                project_model = project_bundle["tfidf_lr" if model_name == "TF-IDF LR" else "third"]
                prob = _probability_by_model(model_name, project_model, text, sender_type, url_summary)
                verdict, abstain = _verdict_for_probability(model_name, prob)
                score_map[model_name] = {"probability": round(float(prob), 4), "verdict": verdict, "abstain": abstain, "top_cues": _keywords_for_text(text)}

        row_verdict = _row_overall_verdict(score_map)
        top_cues = sorted(
            {cue for model in score_map.values() for cue in model["top_cues"]},
            key=lambda item: item.lower(),
        )[:5]
        entries = [
            {"model": "Rules", "probability": score_map["Rules"]["probability"], "verdict": score_map["Rules"]["verdict"], "abstain": score_map["Rules"]["abstain"], "top_cues": score_map["Rules"]["top_cues"]},
            {"model": "TF-IDF LR", "probability": score_map["TF-IDF LR"]["probability"], "verdict": score_map["TF-IDF LR"]["verdict"], "abstain": score_map["TF-IDF LR"]["abstain"], "top_cues": score_map["TF-IDF LR"]["top_cues"]},
            {"model": "Third", "probability": score_map["Third"]["probability"], "verdict": score_map["Third"]["verdict"], "abstain": score_map["Third"]["abstain"], "top_cues": score_map["Third"]["top_cues"]},
        ]
        rows.append(
            {
                "message_id": message_id,
                "campaign_group": str(getattr(row, "campaign_group", "unknown")),
                "channel": channel,
                "label": str(getattr(row, "label", "")).lower(),
                "verdict": row_verdict,
                "abstain": any(entry["abstain"] for entry in entries),
                "model_scores": {name: score_map[name] for name in model_names},
                "top_cues": top_cues,
                "model_rows": entries,
            }
        )

        for model_name in model_names:
            model_pred = score_map[model_name]["verdict"]
            model_results[model_name].append(model_pred)
            if has_labels:
                model_labels[model_name].append(str(label_values.iloc[len(model_labels[model_name])]) if len(model_labels[model_name]) < len(df) else "")

    summary = {
        "rows_scored": len(rows),
        "phishing_rows": sum(1 for row in rows if row["verdict"] == "PHISHING"),
        "legitimate_rows": sum(1 for row in rows if row["verdict"] == "LEGITIMATE"),
        "abstain_rows": sum(1 for row in rows if row["verdict"] == "ABSTAIN"),
        "overall_verdict": "PHISHING" if sum(1 for row in rows if row["verdict"] == "PHISHING") >= sum(1 for row in rows if row["verdict"] == "LEGITIMATE") else "LEGITIMATE",
        "label_column_present": has_labels,
        "warnings": validation_logs,
        "errors": validation_errors,
    }

    result_rows = []
    for row in rows:
        result_rows.append(
            {
                "message_id": row["message_id"],
                "campaign_group": row["campaign_group"],
                "p(Rules)": row["model_scores"]["Rules"]["probability"],
                "p(TF-IDF LR)": row["model_scores"]["TF-IDF LR"]["probability"],
                "p(Third)": row["model_scores"]["Third"]["probability"],
                "verdict": row["verdict"],
                "abstain_flag": row["abstain"],
                "top_cues": ", ".join(row["top_cues"]),
                "model_scores": row["model_scores"],
            }
        )

    if has_labels:
        actual_labels = df["label"].fillna("").astype(str).str.lower().tolist()
        metrics_by_model = {}
        for model_name in model_names:
            pred = [row["model_scores"][model_name]["verdict"] for row in rows]
            metrics = _compute_label_metrics(actual_labels, pred)
            csv_df = df.copy()
            csv_df["predicted"] = pred
            csv_df["predicted"] = csv_df["predicted"].astype(str).str.upper()
            metrics_by_model[model_name] = {
                **metrics,
                "campaign_breakdown": _per_campaign_breakdown(csv_df, model_name),
            }
        summary["metrics_by_model"] = metrics_by_model
        summary["model_predictions"] = {model_name: [row["model_scores"][model_name]["verdict"] for row in rows] for model_name in model_names}
    else:
        summary["metrics_by_model"] = {}
        summary["model_predictions"] = {model_name: [row["model_scores"][model_name]["verdict"] for row in rows] for model_name in model_names}
        summary["notes"] = "Labels were not included in the upload, so only predictive output is reported."

    payload = {
        "summary": summary,
        "rows": result_rows,
        "record_count": len(result_rows),
    }
    if has_labels:
        payload["labels_detected"] = True
    else:
        payload["labels_detected"] = False
    return payload


def generate_sample_template(output_path: str | Path | None = None) -> Path:
    sample = pd.DataFrame(
        [
            {
                "message_id": "mentor_msg_001",
                "channel": "email",
                "subject_or_title": "Urgent account review",
                "body_text": "Verify your account before the login is suspended. Review hxxp://secure[.]portal[.]review/login.",
                "sanitized_url_features": "hxxp://secure[.]portal[.]review/login",
                "sender_domain_type": "lookalike",
                "label": "phishing",
                "campaign_group": "mentor_phish_01",
                "collected_date": "2026-01-01",
                "source_type": "mentor",
            },
            {
                "message_id": "mentor_msg_002",
                "channel": "sms",
                "subject_or_title": "Password reset completed",
                "body_text": "Your password reset was completed by the service desk and no further action is required.",
                "sanitized_url_features": "hxxp://help[.]example[.]com/reset",
                "sender_domain_type": "corporate",
                "label": "legitimate",
                "campaign_group": "mentor_legit_01",
                "collected_date": "2026-01-02",
                "source_type": "mentor",
            },
            {
                "message_id": "mentor_msg_003",
                "channel": "email",
                "subject_or_title": "Final security reminder",
                "body_text": "Final reminder: your security code is due today. Confirm at hxxp://update[.]secure[.]portal/login.",
                "sanitized_url_features": "hxxps://update[.]secure[.]portal/login",
                "sender_domain_type": "unknown",
                "label": "phishing",
                "campaign_group": "mentor_phish_02",
                "collected_date": "2026-01-03",
                "source_type": "mentor",
            },
            {
                "message_id": "mentor_msg_004",
                "channel": "chat",
                "subject_or_title": "Account access check",
                "body_text": "We reviewed your account access and the service desk has already completed the check.",
                "sanitized_url_features": "hxxp://service[.]desk[.]example/account",
                "sender_domain_type": "corporate",
                "label": "legitimate",
                "campaign_group": "mentor_legit_02",
                "collected_date": "2026-01-04",
                "source_type": "mentor",
            },
            {
                "message_id": "mentor_msg_005",
                "channel": "email",
                "subject_or_title": "Billing issue",
                "body_text": "Your invoice is overdue and payment is needed immediately. Review hxxp://billing[.]secure[.]claim/payment.",
                "sanitized_url_features": "hxxp://billing[.]secure[.]claim/payment",
                "sender_domain_type": "lookalike",
                "label": "phishing",
                "campaign_group": "mentor_phish_03",
                "collected_date": "2026-01-05",
                "source_type": "mentor",
            },
        ]
    )
    path = Path(output_path) if output_path else Path.cwd() / "mentor_template.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = sample[DEFAULT_COLUMNS]
    sample.to_csv(path, index=False)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate external mentor CSV files using the PhishShift model suite.")
    parser.add_argument("csv_files", nargs="*", help="One or more CSV files to evaluate.")
    parser.add_argument("--output", default=None, help="Optional output directory for the report files.")
    args = parser.parse_args(argv)

    paths = [Path(item) for item in args.csv_files] if args.csv_files else [Path("mentor.csv")]
    if not paths:
        parser.print_help()
        return 1

    report_dir = Path(args.output) if args.output else Path(__file__).resolve().parents[2] / "reports" / "external"
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = evaluate_csv(paths)
    report_path = report_dir / "mentor_eval.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    csv_rows = payload["rows"]
    result_df = pd.DataFrame(csv_rows)
    result_df.to_csv(report_dir / "mentor_eval_results.csv", index=False)

    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
