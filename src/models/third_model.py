from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


def build_model() -> Pipeline:
    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    strip_accents="unicode",
                    sublinear_tf=True,
                    analyzer="word",
                ),
            ),
            (
                "classifier",
                LinearSVC(class_weight="balanced", random_state=42),
            ),
        ]
    )
    return pipeline
