from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def build_model() -> Pipeline:
    model = Pipeline(
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
                LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42),
            ),
        ]
    )
    return model
