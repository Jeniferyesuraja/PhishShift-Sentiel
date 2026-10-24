from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from src.models.rules import score_message
from src.models.third_model import build_model as build_third_model
from src.models.tfidf_lr import build_model as build_tfidf_model

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean.csv"
REPORT_PATH = ROOT / "reports" / "robustness_drift.json"
CSV_PATH = ROOT / "reports" / "robustness_drift.csv"
MODEL_NAMES = ("rules", "tfidf_lr", "third_model")
PERTURBATION_NAMES = (
    "case",
    "spacing",
    "defang_url",
    "punctuation",
    "synonym_swap",
    "shortener_token",
)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


@lru_cache(maxsize=1)
def _load_models() -> dict[str, object]:
    df = pd.read_csv(DATA_PATH).fillna("")
    text = (df["subject_or_title"].fillna("") + " " + df["body_text"].fillna("")).astype(str)
    labels = df["label"].astype(str).tolist()
    tfidf = build_tfidf_model()
    tfidf.fit(text.tolist(), labels)
    third = build_third_model()
    third.fit(text.tolist(), labels)
    return {"tfidf_lr": tfidf, "third_model": third}


def _probability_for_rules(text: str) -> float:
    url_summary = {"has_shortener": any(token in text.lower() for token in ["bit.ly", "tinyurl", "t.co", "goo.gl"]), "lookalike_score": 0.5}
    score, _ = score_message(text, sender_domain_type="unknown", url_summary=url_summary)
    return round(float(min(max(score, 0.0), 1.0)), 4)


def _probability_for_model(model: object, text: str) -> float:
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba([text])[0]
        labels = getattr(model, "classes_", [])
        if len(labels) and "phishing" in labels:
            idx = int(np.where(labels == "phishing")[0][0])
            return round(float(probs[idx]), 4)
        return round(float(np.max(probs)), 4)
    decision = model.decision_function([text])[0]
    probability = 1.0 / (1.0 + np.exp(-float(decision)))
    return round(float(probability), 4)


def _score_models(text: str) -> dict[str, float]:
    models = _load_models()
    return {
        "rules": _probability_for_rules(text),
        "tfidf_lr": _probability_for_model(models["tfidf_lr"], text),
        "third_model": _probability_for_model(models["third_model"], text),
    }


def make_perturbations(text: str) -> list[dict[str, str]]:
    clean_text = _clean_text(text)
    if not clean_text:
        clean_text = "Urgent verification required for your account access before it is suspended."
    variants = [
        {"name": "case", "text": clean_text.swapcase()},
        {"name": "spacing", "text": re.sub(r"\s+", "  ", clean_text)},
        {"name": "defang_url", "text": clean_text.replace("http://", "hxxp://").replace("https://", "hxxp://").replace(".com", "[.]com").replace(".net", "[.]net")},
        {"name": "punctuation", "text": re.sub(r"([A-Za-z])\s+", r"\1!!! ", clean_text)},
        {
            "name": "synonym_swap",
            "text": clean_text.replace("verify", "confirm").replace("password", "passphrase").replace("suspended", "paused").replace("urgent", "time-sensitive"),
        },
        {"name": "shortener_token", "text": f"{clean_text} bit.ly/secure-login"},
    ]
    return variants


def analyze_drift(message: str) -> dict:
    base_text = _clean_text(message)
    baseline = _score_models(base_text)
    results = []
    for variant in make_perturbations(base_text):
        perturbed_scores = _score_models(variant["text"])
        shift = {model: round(float(perturbed_scores[model] - baseline[model]), 4) for model in MODEL_NAMES}
        results.append(
            {
                "perturbation": variant["name"],
                "baseline": {model: round(float(baseline[model]), 4) for model in MODEL_NAMES},
                "perturbed": {model: round(float(perturbed_scores[model]), 4) for model in MODEL_NAMES},
                "shift": shift,
            }
        )

    average_shift = round(
        float(sum(abs(entry["shift"][model]) for entry in results for model in MODEL_NAMES) / max(1, len(results) * len(MODEL_NAMES))),
        4,
    )
    drift = {
        "message": base_text,
        "rows_processed": int(len(results)),
        "average_score": average_shift,
        "perturbations": PERTURBATION_NAMES,
        "results": results,
        "warning": "Decision support only - not a guarantee of safety.",
        "notes": "Perturbation checks monitor the drift caused by harmless formatting changes and URL token variations without opening links.",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(drift, indent=2), encoding="utf-8")

    csv_rows = []
    for item in results:
        for model in MODEL_NAMES:
            csv_rows.append(
                {
                    "perturbation": item["perturbation"],
                    "model": model,
                    "baseline_probability": item["baseline"][model],
                    "perturbed_probability": item["perturbed"][model],
                    "shift": item["shift"][model],
                }
            )
    pd.DataFrame(csv_rows).to_csv(CSV_PATH, index=False)
    return drift


def compute_robustness() -> dict:
    df = pd.read_csv(DATA_PATH).fillna("")
    phishing_sample = df[df["label"] == "phishing"].head(1)
    if phishing_sample.empty:
        base_message = "Urgent account verification is required before the password reset expires."
    else:
        base_message = " ".join(
            segment for segment in [
                phishing_sample["subject_or_title"].iloc[0],
                phishing_sample["body_text"].iloc[0],
            ]
            if segment
        ).strip()
    return analyze_drift(base_message)


if __name__ == "__main__":
    print(compute_robustness())
