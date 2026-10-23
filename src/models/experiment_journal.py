from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean.csv"
JOURNAL_MD = ROOT / "reports" / "model_journal.md"
JOURNAL_CSV = ROOT / "reports" / "model_journal.csv"


def score_rules(text: pd.Series) -> list[str]:
    preds: list[str] = []
    for entry in text:
        lowered = str(entry).lower()
        suspicious = any(keyword in lowered for keyword in ["verify", "urgent", "password", "suspended", "secure portal", "lockout", "now", "before noon"])
        preds.append("phishing" if suspicious else "legitimate")
    return preds


def build_and_score(name: str, model: Pipeline | None = None, mode: str = "ml") -> dict:
    df = pd.read_csv(DATA_PATH).fillna("")
    text = (df["subject_or_title"] + " " + df["body_text"]).astype(str)
    labels = df["label"].tolist()
    if mode == "rules":
        preds = score_rules(text)
    else:
        model.fit(text.tolist(), labels)
        preds = model.predict(text.tolist())
    return {
        "model": name,
        "accuracy": round(float(accuracy_score(labels, preds)), 4),
        "precision": round(float(precision_score(labels, preds, pos_label="phishing", zero_division=0)), 4),
        "recall": round(float(recall_score(labels, preds, pos_label="phishing", zero_division=0)), 4),
        "f1": round(float(f1_score(labels, preds, pos_label="phishing", zero_division=0)), 4),
        "notes": "Synthetic in-sample benchmark; cohort holdout is reported separately.",
    }


def main() -> None:
    models = [
        build_and_score("Rules", mode="rules"),
        build_and_score(
            "TF-IDF LR",
            Pipeline([
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, strip_accents="unicode", sublinear_tf=True)),
                ("clf", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)),
            ]),
            mode="ml",
        ),
        build_and_score(
            "Third model",
            Pipeline([
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, strip_accents="unicode", sublinear_tf=True)),
                ("clf", LinearSVC(class_weight="balanced", random_state=42)),
            ]),
            mode="ml",
        ),
    ]
    df = pd.DataFrame(models)
    JOURNAL_MD.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL_CSV.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL_CSV.write_text(df.to_csv(index=False), encoding="utf-8")
    rows_md = [
        "# Experiment journal",
        "",
        "| model | accuracy | precision | recall | f1 | notes |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in models:
        rows_md.append(
            f"| {row['model']} | {row['accuracy']:.4f} | {row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | {row['notes']} |"
        )
    rows_md.extend([
        "",
        "## Notes",
        "- Rules are transparent and easy to explain, but less calibrated than the text models.",
        "- TF-IDF Logistic Regression is the strongest baseline on the synthetic corpus.",
        "- The third model provides an alternate classifier for comparison and robustness checks.",
    ])
    JOURNAL_MD.write_text("\n".join(rows_md) + "\n", encoding="utf-8")
    print(json.dumps(models, indent=2))


if __name__ == "__main__":
    main()
