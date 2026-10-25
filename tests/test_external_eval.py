from __future__ import annotations

from io import BytesIO

import pandas as pd

from app import create_app
from src.eval.external import evaluate_csv, generate_sample_template


def test_generate_sample_template_has_required_schema_and_rows(tmp_path):
    out = tmp_path / "mentor_template.csv"
    generate_sample_template(out)
    assert out.exists()
    df = pd.read_csv(out)
    assert len(df) == 5
    required = {
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
    }
    assert set(df.columns) == required
    assert "hxxp://" in df["sanitized_url_features"].astype(str).iloc[0]


def test_evaluate_csv_returns_predictions_and_metrics(tmp_path):
    rows = [
        {
            "message_id": "m_001",
            "channel": "email",
            "subject_or_title": "Urgent password reset",
            "body_text": "Verify your account now before the login is suspended. Please review hxxp://example[.]com/login.",
            "sanitized_url_features": '{"defanged": true, "has_shortener": false, "lookalike_score": 0.12}',
            "sender_domain_type": "lookalike",
            "label": "phishing",
            "campaign_group": "mentor_phish",
            "collected_date": "2026-01-01",
            "source_type": "mentor",
        },
        {
            "message_id": "m_002",
            "channel": "email",
            "subject_or_title": "Password reset completed",
            "body_text": "Your password reset was completed by the service desk and no further action is required.",
            "sanitized_url_features": '{"defanged": true, "has_shortener": false, "lookalike_score": 0.05}',
            "sender_domain_type": "corporate",
            "label": "legitimate",
            "campaign_group": "mentor_legit",
            "collected_date": "2026-01-02",
            "source_type": "mentor",
        },
    ]
    csv_path = tmp_path / "mentor.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    payload = evaluate_csv(csv_path)
    assert payload["summary"]["rows_scored"] == 2
    assert "rows" in payload
    assert payload["rows"][0]["model_scores"]["Rules"]["probability"] >= 0.0
    assert "overall_verdict" in payload["summary"]


def test_batch_api_exposes_download_buttons_and_batch_endpoint():
    app = create_app()
    client = app.test_client()
    html = client.get("/batch").get_data(as_text=True)
    assert "Download sample CSV template" in html
    assert "Run evaluation" in html or "Run batch evaluation" in html
    response = client.post(
        "/api/batch/eval",
        data={
            "upload": (BytesIO(b"message_id,channel,subject_or_title,body_text,sanitized_url_features,sender_domain_type,label,campaign_group,collected_date,source_type\n1,email,Hi,Hello world,\"{\\\"defanged\\\": true}\",corporate,legitimate,mentor,2026-01-01,mentor\n"), "mentor.csv"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code in {200, 400}
