from __future__ import annotations

from flask import Flask, request


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    app.config["SECRET_KEY"] = "demo-secret-key"

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    @app.get("/")
    def index():
        return """<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>PhishShift</title>
<style>
body { font-family: Arial, sans-serif; background: #0b1020; color: #e8edf9; margin: 0; padding: 32px; }
.container { max-width: 960px; margin: 0 auto; }
.card { background: rgba(17,24,39,0.9); border: 1px solid rgba(148,163,184,0.25); border-radius: 16px; padding: 24px; box-shadow: 0 12px 30px rgba(15,23,42,0.5); }
.banner { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.35); color: #f8d7da; padding: 12px 16px; border-radius: 12px; margin-bottom: 20px; }
label { display: block; margin: 12px 0 6px; } textarea, select { width: 100%; box-sizing: border-box; padding: 12px; border-radius: 10px; border: 1px solid #475569; background: #020817; color: #f8fafc; }
button { background: linear-gradient(135deg, #22c55e, #0ea5e9); border: none; padding: 12px 18px; color: #04111d; font-weight: 700; border-radius: 10px; cursor: pointer; }
.risk { font-size: 42px; font-weight: 700; }
.small { color: #cbd5e1; }
</style>
</head>
<body>
<div class=\"container\">
  <div class=\"banner\">Decision support only - not a guarantee of safety. No links are opened.</div>
  <div class=\"card\">
    <h1>PhishShift Message Risk Scanner</h1>
    <p class=\"small\">Synthetic helpdesk triage demo for phishing and legitimate urgency review.</p>
    <form id=\"scanner\">
      <label for=\"channel\">Channel</label>
      <select id=\"channel\" name=\"channel\">
        <option value=\"email\">email</option>
        <option value=\"sms\">sms</option>
      </select>
      <label for=\"subject\">Subject</label>
      <textarea id=\"subject\" rows=\"2\">Urgent password reset required</textarea>
      <label for=\"body\">Body</label>
      <textarea id=\"body\" rows=\"8\">We noticed unusual activity. Verify your account now using hxxp://secure[.]portal[.]review/login to avoid suspension.</textarea>
      <button type=\"submit\">Scan</button>
    </form>
    <div id=\"result\" style=\"margin-top: 24px;\"></div>
  </div>
</div>
<script>
const form = document.getElementById('scanner');
const result = document.getElementById('result');
form.addEventListener('submit', (event) => {
  event.preventDefault();
  const payload = { channel: document.getElementById('channel').value, subject: document.getElementById('subject').value, body: document.getElementById('body').value };
  result.innerHTML = '<div class="small">Scanning…</div>';
  fetch('/api/scan', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  }).then(r => r.json()).then(data => {
    result.innerHTML = '<div class="risk">' + data.risk + '/100</div><div><strong>Verdict:</strong> ' + data.verdict + '</div><div><strong>Explanation:</strong> ' + data.explanation + '</div>';
  }).catch(() => {
    result.innerHTML = '<div class="small">Scan failed.</div>';
  });
});
</script>
</body>
</html>"""

    @app.post("/api/scan")
    def scan():
        from src.models.rules import score_message

        payload = request.get_json(silent=True) or {}
        channel = str(payload.get("channel", "email")).lower()
        subject = str(payload.get("subject", ""))
        body = str(payload.get("body", ""))
        text = f"{subject} {body}"
        score, cues = score_message(text, channel, {"has_shortener": "short" in text.lower(), "lookalike_score": 0.7})
        verdict = "PHISHING-LIKELY" if score >= 0.7 else "SUSPICIOUS" if score >= 0.45 else "SAFE-LOOKING"
        return {
            "risk": int(score * 100),
            "verdict": verdict,
            "explanation": ", ".join(cues[:3]) or "No dominant risk cues detected.",
            "cues": cues,
        }

    return app
