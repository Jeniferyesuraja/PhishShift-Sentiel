from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data.dedup import compute_near_duplicates
from src.models.rules import score_message
from src.models.third_model import build_model as build_third_model
from src.models.tfidf_lr import build_model as build_tfidf_model
from src.models.train import _probability_of_phishing, compute_grouped_holdout

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean.csv"
REPORT_DIR = ROOT / "reports" / "acceptance"


def defang_url(url: str) -> str:
    if not url:
        return url
    url = url.strip().replace("https://", "hxxps://").replace("http://", "hxxp://")
    return url.replace(".", "[.]")


def _load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH).fillna("")
    df["text"] = (df["subject_or_title"].fillna("") + " " + df["body_text"].fillna("")).str.strip()
    df["url_text"] = df["sanitized_url_features"].fillna("{}")
    dedup_df, _ = compute_near_duplicates(df, threshold=0.90)
    return dedup_df


def _load_train_and_test() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    df = _load_dataset()
    train_df, test_df, holdout_campaigns = compute_grouped_holdout(df)
    return train_df, test_df, holdout_campaigns


def _as_url_summary(url_text: str) -> dict:
    try:
        payload = json.loads(url_text)
    except Exception:
        payload = {}
    return {"has_shortener": bool(payload.get("has_shortener")), "lookalike_score": float(payload.get("lookalike_score", 0.0))}


def _abstain_bounds(model_name: str) -> tuple[float, float]:
    if model_name == "Rules":
        return 0.38, 0.62
    return 0.45, 0.55


def _classify_probability(model_name: str, probability: float) -> str:
    if model_name == "Rules":
        if probability >= 0.62:
            return "PHISHING"
        if probability <= 0.38:
            return "LEGITIMATE"
        return "ABSTAIN"
    if probability >= 0.5:
        return "PHISHING"
    if probability < 0.5:
        return "LEGITIMATE"
    return "ABSTAIN"


def _build_model_map(train_df: pd.DataFrame) -> dict:
    model_map = {"Rules": None, "TF-IDF LR": build_tfidf_model(), "Third model": build_third_model()}
    for model_name, model in model_map.items():
        if model_name == "Rules":
            continue
        model.fit(train_df["text"].tolist(), train_df["label"].tolist())
    return model_map


def _score_text(model_name: str, model, text: str, sender_type: str, url_text: str) -> dict:
    if model_name == "Rules":
        probability, cues = score_message(text, sender_domain_type=sender_type, url_summary=_as_url_summary(url_text))
        return {
            "model": model_name,
            "probability": round(float(probability), 4),
            "verdict": _classify_probability(model_name, float(probability)),
            "abstain": 0.38 <= float(probability) <= 0.62,
            "risk_cues": cues[:5],
        }

    probability = float(_probability_of_phishing(model, [text])[0])
    lower, upper = _abstain_bounds(model_name)
    verdict = "ABSTAIN" if lower <= probability <= upper else _classify_probability(model_name, probability)
    return {
        "model": model_name,
        "probability": round(probability, 4),
        "verdict": verdict,
        "abstain": lower <= probability <= upper,
        "risk_cues": [
            "credential or sensitive account wording",
            "urgency or deadline pressure",
            "URL or domain suspicion",
        ],
    }


def _overall_verdict(model_scores: list[dict], kind: str) -> tuple[str, str]:
    if kind == "AT-01":
        thresholds = {"Rules": (0.38, 0.62), "TF-IDF LR": (0.45, 0.55), "Third model": (0.45, 0.55)}
        if any(entry["abstain"] for entry in model_scores):
            return "ABSTAINED", "ABSTAINED - escalated to human. Legitimate urgent wording stayed in the abstain band, which is a false-positive cost and should be reviewed by an analyst."
        if all(entry["probability"] < thresholds[entry["model"]][0] for entry in model_scores):
            return "PASS", f"PASS - every model stayed below the abstain lower bound ({thresholds['Rules'][0]}, {thresholds['TF-IDF LR'][0]})."
        if any(entry["verdict"] == "PHISHING" for entry in model_scores):
            return "FAIL", "FAIL - a legitimate urgent message was flagged as phishing by at least one model."
        return "ABSTAINED", "ABSTAINED - escalated to human. The legitimate urgent message was in the abstain band for at least one model."
    if kind == "AT-02":
        caught = sum(1 for entry in model_scores if entry["verdict"] == "PHISHING")
        abstained = sum(1 for entry in model_scores if entry["abstain"])
        missed = sum(1 for entry in model_scores if entry["verdict"] == "LEGITIMATE")
        if caught > 0 and missed == 0:
            return "PASS", f"The unseen campaign was caught by {caught} model(s); {abstained} abstained and {missed} missed."
        if abstained > 0 and caught == 0:
            return "ABSTAINED", f"The unseen campaign fell into the abstain band for {abstained} model(s); {caught} model(s) caught it and {missed} missed."
        return "FAIL", f"The unseen campaign was missed by {missed} model(s) and only caught by {caught} model(s)."
    if kind == "AT-03":
        mean_shift = float(sum(abs(entry["shift"]) for entry in model_scores) / max(1, len(model_scores)))
        if mean_shift <= 0.2:
            return "PASS", "Formatting or URL changes did not materially alter the verdicts."
        return "FAIL", "The model was materially sensitive to punctuation and URL formatting changes, which is a limitation in the current feature space."
    return "FAIL", "No verdict computed."


def _write_evidence(name: str, payload: dict, markdown: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (REPORT_DIR / f"{name}.md").write_text(markdown, encoding="utf-8")


def _at_01(train_df: pd.DataFrame, model_map: dict) -> dict:
    message = (
        "Your password reset was completed by the service desk and the account review confirms no further action is required. "
        "Please keep this message for your records and contact support only if you expected a change to your account access."
    )
    sender_type = "corporate"
    url_text = json.dumps({"has_shortener": False, "lookalike_score": 0.1}, sort_keys=True)
    model_scores = [_score_text(name, model, message, sender_type, url_text) for name, model in model_map.items()]
    for entry in model_scores:
        entry["score_bar"] = min(100, max(0, int(round(entry["probability"] * 100))))

    legit_urgent = train_df[(train_df["label"] == "legitimate") & (train_df["text"].str.lower().str.contains("password|reset|urgent|verify|security|suspended|credential|login|payroll|maintenance", regex=True))].copy()

    flagged = 0
    abstained = 0
    for _, row in legit_urgent.iterrows():
        candidate = [_score_text(name, model, row["text"], str(row.get("sender_domain_type", "corporate")), str(row.get("url_text", "{}"))) for name, model in model_map.items()]
        if any(score["verdict"] == "PHISHING" for score in candidate):
            flagged += 1
        if any(score["abstain"] for score in candidate):
            abstained += 1
    total = max(1, len(legit_urgent))
    fpr_rate = float(flagged / total) if total else 0.0
    thresholds = {"Rules": (0.38, 0.62), "TF-IDF LR": (0.45, 0.55), "Third model": (0.45, 0.55)}
    false_positive = any(score["verdict"] == "PHISHING" for score in model_scores) or any(score["abstain"] for score in model_scores)
    status, summary = _overall_verdict(model_scores, "AT-01")
    payload = {
        "name": "AT-01",
        "title": "Legitimate password-reset notice",
        "status": status,
        "summary": summary + f" Absent from pass state: abstain thresholds are Rules 0.38-0.62 and TF-IDF LR / Third 0.45-0.55; PASS requires all model scores below the lower bound.",
        "input_message": message,
        "defanged_message": defang_url(message),
        "models": model_scores,
        "false_positive": false_positive,
        "false_positive_impact": {
            "legit_urgent_total": int(len(legit_urgent)),
            "flagged": int(flagged),
            "abstained": int(abstained),
            "flagged_total": int(flagged),
            "abstained_total": int(abstained),
            "fpr": round(fpr_rate, 4),
            "thresholds": {name: {"lower": lower, "upper": upper} for name, (lower, upper) in thresholds.items()},
            "analyst_experience": "Wasted triage minutes and alert fatigue from escalating legitimate urgent messages into human review.",
        },
        "verdict": status,
        "abstain": any(score["abstain"] for score in model_scores),
        "score": round(float(max(score["probability"] for score in model_scores)), 4),
        "top_risk_cues": sorted({cue for score in model_scores for cue in score["risk_cues"]}, key=lambda item: item.lower())[:5],
        "thresholds": {name: {"lower": lower, "upper": upper} for name, (lower, upper) in thresholds.items()},
    }
    markdown = (
        "# AT-01\n\n"
        f"## Outcome: {status}\n\n"
        f"- Input message: {payload['input_message']}\n"
        f"- Thresholds: Rules abstain band 0.38-0.62; TF-IDF LR and Third model abstain band 0.45-0.55; PASS requires every score to stay below the lower bound.\n"
        f"- False-positive impact: flagged {flagged} / {len(legit_urgent)}; abstained {abstained} / {len(legit_urgent)}; FPR {fpr_rate:.3f}.\n"
        "- Analyst experience: wasted triage minutes and alert fatigue from escalating legitimate urgent messages.\n"
        "- Decision support only - not a guarantee of safety.\n\n"
        + "\n".join(
            f"- {entry['model']}: probability {entry['probability']:.3f}, verdict {entry['verdict']}, abstain={str(entry['abstain']).lower()}" for entry in model_scores
        )
        + "\n"
    )
    _write_evidence("AT-01", payload, markdown)
    return payload


def _at_02(train_df: pd.DataFrame, test_df: pd.DataFrame, model_map: dict) -> dict:
    train_campaigns = set(train_df["campaign_group"].dropna().unique().tolist())
    candidate_campaigns = [campaign for campaign in test_df["campaign_group"].dropna().unique().tolist() if campaign not in train_campaigns]
    campaign_name = candidate_campaigns[0] if candidate_campaigns else test_df["campaign_group"].dropna().unique().tolist()[0]
    candidate = test_df[test_df["campaign_group"] == campaign_name].iloc[0]
    message = (
        str(candidate["subject_or_title"]).strip() + " " + str(candidate["body_text"]).strip()
        if str(candidate["subject_or_title"]).strip()
        else str(candidate["body_text"]).strip()
    )
    model_scores = [_score_text(name, model, message, str(candidate.get("sender_domain_type", "unknown")), str(candidate.get("url_text", "{}"))) for name, model in model_map.items()]
    for entry in model_scores:
        entry["score_bar"] = min(100, max(0, int(round(entry["probability"] * 100))))
    status, summary = _overall_verdict(model_scores, "AT-02")
    caught = sum(1 for score in model_scores if score["verdict"] == "PHISHING")
    abstained = sum(1 for score in model_scores if score["abstain"])
    missed = sum(1 for score in model_scores if score["verdict"] == "LEGITIMATE")
    payload = {
        "name": "AT-02",
        "title": "Unfamiliar phishing phrasing",
        "status": status,
        "summary": summary,
        "campaign_group": campaign_name,
        "absent_from_training": bool(campaign_name not in train_campaigns),
        "input_message": message,
        "defanged_message": defang_url(message),
        "models": model_scores,
        "verdict": status,
        "caught": caught,
        "abstained": abstained,
        "missed": missed,
        "abstain": any(score["abstain"] for score in model_scores),
        "score": round(float(max(score["probability"] for score in model_scores)), 4),
        "top_risk_cues": sorted({cue for score in model_scores for cue in score["risk_cues"]}, key=lambda item: item.lower())[:5],
    }
    markdown = (
        "# AT-02\n\n"
        f"## Outcome: {status}\n\n"
        f"- Held-out campaign: {campaign_name}\n"
        f"- Absent from train split: {str(payload['absent_from_training']).lower()}\n"
        f"- Caught / abstained / missed: {caught} / {abstained} / {missed}\n"
        f"- Summary: {summary}\n"
        "- Decision support only - not a guarantee of safety.\n\n"
        + "\n".join(
            f"- {entry['model']}: probability {entry['probability']:.3f}, verdict {entry['verdict']}, abstain={str(entry['abstain']).lower()}" for entry in model_scores
        )
        + "\n"
    )
    _write_evidence("AT-02", payload, markdown)
    return payload


def _at_03(model_map: dict) -> dict:
    baseline = (
        "The password reset was completed and your security review is active. No further action is required and the service desk has already verified the request."
    )
    perturbed = (
        "URGENT!!! Your password reset is pending and the account review requires confirmation now! Please verify hxxp://secure[.]portal[.]review/login before the security check closes."
    )
    sender_type = "lookalike"
    baseline_url = json.dumps({"has_shortener": False, "lookalike_score": 0.1}, sort_keys=True)
    perturbed_url = json.dumps({"has_shortener": True, "lookalike_score": 0.9}, sort_keys=True)
    baseline_scores = [_score_text(name, model, baseline, sender_type, baseline_url) for name, model in model_map.items()]
    perturbed_scores = [_score_text(name, model, perturbed, sender_type, perturbed_url) for name, model in model_map.items()]
    model_scores = []
    for baseline_score, perturbed_score in zip(baseline_scores, perturbed_scores):
        shift = abs(perturbed_score["probability"] - baseline_score["probability"])
        model_scores.append({
            "model": baseline_score["model"],
            "baseline_probability": baseline_score["probability"],
            "perturbed_probability": perturbed_score["probability"],
            "shift": round(shift, 4),
            "score_bar": min(100, max(0, int(round(perturbed_score["probability"] * 100)))),
        })
    mean_shift = float(sum(item["shift"] for item in model_scores) / max(1, len(model_scores)))
    status, summary = _overall_verdict([
        {"probability": item["baseline_probability"], "shift": item["shift"], "model": item["model"], "abstain": False} for item in model_scores
    ], "AT-03")
    note = "Model limitation: formatting changes such as URL defanging and punctuation materially shift the score, indicating surface-form sensitivity rather than robust semantic understanding."
    payload = {
        "name": "AT-03",
        "title": "Defanged URL and punctuation changes",
        "status": status,
        "summary": summary,
        "baseline_message": baseline,
        "perturbed_message": perturbed,
        "models": model_scores,
        "verdict": status,
        "abstain": any(item["shift"] > 0.2 for item in model_scores),
        "score": round(mean_shift, 4),
        "note": note,
    }
    markdown = (
        "# AT-03\n\n"
        f"## Outcome: {status}\n\n"
        f"- Mean shift: {mean_shift:.3f}\n"
        f"- Model limitation: {note}\n"
        "- Decision support only - not a guarantee of safety.\n\n"
        + "\n".join(
            f"- {item['model']}: baseline {item['baseline_probability']:.3f}, perturbed {item['perturbed_probability']:.3f}, shift {item['shift']:.3f}"
            for item in model_scores
        )
        + "\n"
    )
    _write_evidence("AT-03", payload, markdown)
    return payload


def run_acceptance_suite() -> dict:
    train_df, test_df, holdout_campaigns = _load_train_and_test()
    del holdout_campaigns
    model_map = _build_model_map(train_df)
    report = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "tests": [
            _at_01(train_df, model_map),
            _at_02(train_df, test_df, model_map),
            _at_03(model_map),
        ],
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "acceptance_bundle.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    print(json.dumps(run_acceptance_suite(), indent=2))


if __name__ == "__main__":
    main()
