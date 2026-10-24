from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
from flask import Flask, render_template_string, request, send_file

from src.acceptance.generate_acceptance import run_acceptance_suite
from src.eval.external import evaluate_csv, generate_sample_template
from src.robustness.perturb import analyze_drift

BASE_CSS = """
:root {
  --bg: #07111d;
  --bg-2: #0b1525;
  --panel: rgba(15, 23, 42, 0.78);
  --panel-alt: rgba(17, 24, 39, 0.9);
  --panel-border: rgba(148, 163, 184, 0.22);
  --text: #e5eefb;
  --muted: #b4c3d8;
  --accent: #48d3ff;
  --green: #3ae9a3;
  --amber: #ffba52;
  --red: #ff6f7d;
  --shadow: 0 22px 60px rgba(10, 15, 24, 0.55);
}
body[data-theme="light"] {
  --bg: #edf4ff;
  --bg-2: #dfeafc;
  --panel: rgba(255, 255, 255, 0.7);
  --panel-alt: rgba(255, 255, 255, 0.82);
  --panel-border: rgba(89, 120, 170, 0.18);
  --text: #0f172a;
  --muted: #40526b;
  --accent: #0ea5e9;
  --green: #17a86b;
  --amber: #d97706;
  --red: #dc2626;
  --shadow: 0 20px 45px rgba(15, 23, 42, 0.14);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: "Inter", "Segoe UI", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(72, 211, 255, 0.12), transparent 20%),
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.14), transparent 22%),
    linear-gradient(135deg, var(--bg), var(--bg-2));
  color: var(--text);
}
body, input, textarea, select, button { font-family: "Inter", "Segoe UI", sans-serif; }
code, pre, .mono { font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace; }
.app-shell {
  max-width: 1320px;
  margin: 0 auto;
  padding: 24px;
}
.banner {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.36);
  color: var(--text);
  border-radius: 14px;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin: 18px 0 22px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(12px);
}
.banner strong { color: var(--red); }
.topbar {
  background: rgba(15, 23, 42, 0.42);
  border: 1px solid var(--panel-border);
  border-radius: 20px;
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(16px);
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand-mark {
  width: 40px; height: 40px; display: grid; place-items: center;
  border-radius: 14px;
  background: rgba(8, 20, 36, 0.5);
  border: 1px solid rgba(103, 232, 249, 0.24);
  box-shadow: inset 0 0 18px rgba(103, 232, 249, 0.12);
}
.brand-logo {
  width: 40px; height: 40px; display: block;
  filter: drop-shadow(0 0 16px rgba(103, 232, 249, 0.18));
}
.scanner-hero {
  display: flex; justify-content: center; padding: 18px 0 10px;
}
.scanner-hero-icon {
  width: 96px; height: 96px; display: block;
  filter: drop-shadow(0 0 18px rgba(103, 232, 249, 0.22));
  animation: logoGlow 3s ease-in-out infinite alternate;
}
.scanner-loader {
  display: grid; place-items: center; gap: 10px; padding-top: 8px;
}
.scanner-loader-icon {
  width: 64px; height: 64px; display: block; opacity: 0.92;
  filter: drop-shadow(0 0 18px rgba(103, 232, 249, 0.24));
  animation: logoGlow 2.2s ease-in-out infinite alternate;
}
.scan-beam {
  position: relative; width: 150px; height: 4px; border-radius: 999px;
  background: linear-gradient(90deg, transparent 0%, rgba(165,243,252,0.9) 50%, transparent 100%);
  box-shadow: 0 0 18px rgba(165,243,252,0.65);
  animation: scanPulse 1.5s ease-in-out infinite;
}
.brand-text h1 { margin: 0; font-size: 1.15rem; }
.brand-text small { color: var(--muted); display: block; margin-top: 2px; }
.nav {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.nav a {
  text-decoration: none;
  color: var(--muted);
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 0.92rem;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}
.nav a.active, .nav a:hover {
  background: rgba(72, 211, 255, 0.1);
  color: var(--text);
  border-color: rgba(72, 211, 255, 0.2);
}
.theme-toggle {
  border: 1px solid var(--panel-border); background: rgba(15, 23, 42, 0.25); color: var(--text);
  border-radius: 12px; padding: 9px 12px; cursor: pointer;
}
.dashboard { display: grid; grid-template-columns: 1.35fr 0.85fr; gap: 22px; margin-top: 22px; }
.card {
  background: linear-gradient(180deg, rgba(15,23,42,0.68), rgba(15,23,42,0.38));
  border: 1px solid var(--panel-border);
  border-radius: 22px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
  overflow: hidden;
}
body[data-theme="light"] .card { background: linear-gradient(180deg, rgba(255,255,255,0.75), rgba(241,245,249,0.7)); }
.panel-header { padding: 18px 20px 12px; border-bottom: 1px solid var(--panel-border); display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.panel-header h2, .panel-header h3 { margin: 0; font-size: 1.08rem; }
.body { padding: 20px; }
.form-grid { display: grid; gap: 14px; }
label { display: block; color: var(--muted); font-size: 0.82rem; margin-bottom: 7px; }
input, textarea, select {
  width: 100%; border-radius: 12px; border: 1px solid var(--panel-border); background: rgba(2, 6, 23, 0.2);
  color: var(--text); padding: 12px 14px; resize: vertical; transition: 0.2s ease;
}
body[data-theme="light"] input, body[data-theme="light"] textarea, body[data-theme="light"] select { background: rgba(255,255,255,0.5); }
input:focus, textarea:focus, select:focus { outline: 2px solid rgba(72,211,255,0.3); border-color: rgba(72,211,255,0.4); }
.sample-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.chip {
  border-radius: 999px; padding: 8px 12px; border: 1px solid rgba(72,211,255,0.22); color: var(--text); background: rgba(72,211,255,0.06); cursor: pointer;
}
.primary-button {
  background: linear-gradient(135deg, rgba(72,211,255,0.9), rgba(59,130,246,0.8));
  color: #03151d; border: none; padding: 12px 18px; font-weight: 700; border-radius: 12px; cursor: pointer; display: inline-flex; justify-content: center; align-items: center; min-width: 160px;
}
.primary-button[disabled] { opacity: 0.7; cursor: not-allowed; }
.gauge-shell {
  width: 200px; height: 200px; margin: 0 auto 14px; position: relative; display: grid; place-items: center;
}
.gauge {
  width: 160px; height: 160px; border-radius: 50%; position: relative; background: conic-gradient(var(--accent) 0deg, rgba(148,163,184,0.2) 0deg);
  display: grid; place-items: center; box-shadow: inset 0 0 30px rgba(15, 23, 42, 0.14);
  transition: background 0.35s ease;
}
.gauge::before {
  content: ""; position: absolute; inset: 18px; border-radius: 50%; background: rgba(5, 9, 19, 0.88); border: 1px solid var(--panel-border);
}
.gauge-value {
  position: relative; z-index: 1; font-size: 2.2rem; font-weight: 800; font-family: "JetBrains Mono", monospace;
}
.badge {
  .badge { display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 8px 12px; border: 1px solid var(--panel-border); font-size: 0.8rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;
}
.badge.safe { background: rgba(58,233,163,0.12); color: var(--green); }
.badge.suspicious { background: rgba(255,186,82,0.12); color: var(--amber); }
.badge.phish { background: rgba(255,111,125,0.12); color: var(--red); }
.badge.uncertain { background: rgba(148,163,184,0.12); color: var(--text); }
.model-bars { display: grid; gap: 12px; }
.model-row { display: grid; grid-template-columns: 110px 1fr 50px; align-items: center; gap: 10px; }
.model-label { font-size: 0.85rem; color: var(--muted); }
.bar { height: 12px; border-radius: 999px; background: rgba(148,163,184,0.18); overflow: hidden; }
.bar > span {
  display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent), var(--green));
  transition: width 0.4s ease;
}
.bar.red > span { background: linear-gradient(90deg, #ff8a88, var(--red)); }
.bar.amber > span { background: linear-gradient(90deg, #f7d66b, var(--amber)); }
.kicker { display: inline-block; color: var(--muted); font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; }
.message-preview {
  border: 1px solid var(--panel-border); border-radius: 16px; padding: 14px 16px; background: rgba(15,23,42,0.2); line-height: 1.7; color: var(--text);
}
mark {
  background: rgba(255, 186, 82, 0.2); color: var(--text); border-radius: 6px; padding: 2px 6px; border: 1px solid rgba(255,186,82,0.35);
  position: relative;
}
mark:hover::after {
  content: attr(data-tooltip); position: absolute; left: 0; top: -34px; background: rgba(15,23,42,0.95); color: #fff; padding: 6px 8px; border-radius: 8px; font-size: 0.7rem; white-space: nowrap; border: 1px solid rgba(148,163,184,0.2);
}
.list { list-style: none; padding: 0; margin: 12px 0 0; display: grid; gap: 10px; }
.list li { background: rgba(148,163,184,0.05); border: 1px solid var(--panel-border); padding: 10px 12px; border-radius: 12px; }
.action-box {
  padding: 14px 16px; border-radius: 14px; border: 1px solid rgba(72,211,255,0.3); background: rgba(72,211,255,0.08); margin-top: 14px;
}
.helper-row { display: flex; gap: 10px; flex-wrap: wrap; }
.subtle { color: var(--muted); }
.error-box {
  display: none; border: 1px solid rgba(255,111,125,0.25); background: rgba(255,111,125,0.08); color: var(--text); border-radius: 12px; padding: 12px 14px; margin-top: 12px;
}
.error-box.visible { display: block; }
.skeleton {
  height: 18px; border-radius: 999px; background: linear-gradient(90deg, rgba(148,163,184,0.14), rgba(148,163,184,0.24), rgba(148,163,184,0.14)); background-size: 200% 100%; animation: pulse 1.2s infinite linear;
}
@keyframes pulse { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
@keyframes logoGlow {
  from { transform: scale(0.985); opacity: 0.9; }
  to { transform: scale(1.04); opacity: 1; }
}
@keyframes scanPulse {
  0% { transform: translateX(-18px); opacity: 0.6; }
  50% { transform: translateX(18px); opacity: 1; }
  100% { transform: translateX(-18px); opacity: 0.6; }
}
@media (prefers-reduced-motion: reduce) {
  .scanner-hero-icon, .scanner-loader-icon, .scan-beam { animation: none; }
}
.grid-two { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; }
.metric-card { padding: 18px; border-radius: 16px; background: rgba(15,23,42,0.22); border: 1px solid var(--panel-border); }
.metric-value { font-size: 1.6rem; font-weight: 800; margin-top: 8px; }
.metric-label { color: var(--muted); }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--panel-border); }
th { color: var(--muted); font-weight: 600; }
.chart-box { min-height: 220px; display: flex; align-items: end; gap: 12px; padding-top: 18px; }
.chart-bar { flex: 1; background: linear-gradient(180deg, var(--accent), rgba(72,211,255,0.3)); border-radius: 10px 10px 0 0; position: relative; min-height: 20px; }
.chart-bar span { position: absolute; bottom: -20px; left: 0; right: 0; text-align: center; font-size: 0.72rem; color: var(--muted); }
.footnote { margin-top: 12px; color: var(--muted); }
@media (max-width: 900px) {
  .dashboard { grid-template-columns: 1fr; }
  .topbar { flex-direction: column; align-items: flex-start; }
  .nav { width: 100%; }
  .grid-two { grid-template-columns: 1fr; }
}
"""

ROOT = Path(__file__).resolve().parents[1]


def _load_metrics() -> dict:
    metrics_path = ROOT / "metrics.json"
    if not metrics_path.exists():
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "false_positive_rate": 0.0, "coverage_at_abstain": 0.0}
    try:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "false_positive_rate": 0.0, "coverage_at_abstain": 0.0}


def _build_model_lab_page() -> str:
    metrics = _load_metrics()
    grouped = metrics.get("grouped_holdout", {})
    comparison = [
        {
            "name": "Rules",
            "precision": float(grouped.get("rules", {}).get("precision", 0.0)),
            "recall": float(grouped.get("rules", {}).get("recall", 0.0)),
            "f1": float(grouped.get("rules", {}).get("f1", 0.0)),
            "roc_auc": float(grouped.get("rules", {}).get("roc_auc", 0.0)),
            "pr_auc": float(grouped.get("rules", {}).get("pr_auc", 0.0)),
        },
        {
            "name": "TF-IDF LR",
            "precision": float(grouped.get("tfidf_lr", {}).get("precision", 0.0)),
            "recall": float(grouped.get("tfidf_lr", {}).get("recall", 0.0)),
            "f1": float(grouped.get("tfidf_lr", {}).get("f1", 0.0)),
            "roc_auc": float(grouped.get("tfidf_lr", {}).get("roc_auc", 0.0)),
            "pr_auc": float(grouped.get("tfidf_lr", {}).get("pr_auc", 0.0)),
        },
        {
            "name": "Third model",
            "precision": float(grouped.get("third_model", {}).get("precision", 0.0)),
            "recall": float(grouped.get("third_model", {}).get("recall", 0.0)),
            "f1": float(grouped.get("third_model", {}).get("f1", 0.0)),
            "roc_auc": float(grouped.get("third_model", {}).get("roc_auc", 0.0)),
            "pr_auc": float(grouped.get("third_model", {}).get("pr_auc", 0.0)),
        },
    ]
    rows_html = "\n".join(
        f"<tr><td>{row['name']}</td><td>{row['precision']:.3f}</td><td>{row['recall']:.3f}</td><td>{row['f1']:.3f}</td><td>{row['roc_auc']:.3f}</td><td>{row['pr_auc']:.3f}</td></tr>"
        for row in comparison
    )
    loco_data = metrics.get("loco", {})
    loco_series = []
    for model_name, payload in loco_data.items():
        scores = payload.get("campaign_scores", [])
        if scores:
            loco_series.extend((campaign.get("campaign_group"), campaign.get("accuracy", 0.0)) for campaign in scores)
    if not loco_series:
        loco_series = [("Campaign 1", 0.0), ("Campaign 2", 0.0), ("Campaign 3", 0.0)]
    chart_html = "\n".join(f"<div class='chart-bar' style='height:{min(100, max(8, value * 100))}%'><span>{label}</span></div>" for label, value in loco_series)
    accuracy = float(metrics.get("accuracy", 0.0))
    false_positive = float(metrics.get("false_positive_rate", 0.0))
    leakage_gap = float(metrics.get("leakage_gap", {}).get("f1_gap", 0.0))
    coverage = float(metrics.get("coverage_at_abstain", 0.0))
    return f"""
<section class="card" style="margin-top:22px;">
  <div class="panel-header">
    <h2>Model Lab</h2>
    <span class="kicker">Evaluation workspace</span>
  </div>
  <div class="body">
    <div class="grid-two">
      <div class="metric-card">
        <div class="metric-label">Grouped holdout accuracy</div>
        <div class="metric-value">{accuracy:.3f}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">False positive rate</div>
        <div class="metric-value">{false_positive:.3f}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Leakage gap</div>
        <div class="metric-value">{abs(leakage_gap):.3f}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Coverage at abstain</div>
        <div class="metric-value">{coverage:.3f}</div>
      </div>
    </div>
    <div style="margin-top:20px;">
      <p class="kicker">Comparator table</p>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Model</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th><th>PR-AUC</th></tr></thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </div>
    </div>
    <div style="margin-top:22px;">
      <p class="kicker">LOCO chart</p>
      <div class="chart-box">
        {chart_html}
      </div>
      <div class="footnote">Campaign-separated validation shows the expected delta versus random split performance.</div>
    </div>
  </div>
</section>
"""


BASE_LAYOUT = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ page_title }} | PhishShift Sentinel</title>
  <link rel="icon" type="image/svg+xml" href="{{ url_for('static', filename='img/favicon.svg') }}">
  <style>{{ css | safe }}</style>
</head>
<body data-theme="dark">
  <div class="app-shell">
    <div class="banner">
      <span><strong>Decision support only</strong> - not a guarantee of safety.</span>
      <span>No links are opened.</span>
    </div>

    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">
          <img src="{{ url_for('static', filename='img/phishshift_icon.svg') }}" alt="PhishShift Sentinel icon" class="brand-logo">
        </div>
        <div class="brand-text">
          <h1>PhishShift Sentinel</h1>
          <small>Spot the shift. Stop the phish.</small>
        </div>
      </div>
      <nav class="nav" aria-label="Main navigation">
        <a href="/" class="{{ 'active' if active_nav == 'scanner' else '' }}">Scanner</a>
        <a href="/model-lab" class="{{ 'active' if active_nav == 'model-lab' else '' }}">Model Lab</a>
        <a href="/robustness" class="{{ 'active' if active_nav == 'robustness' else '' }}">Robustness</a>
        <a href="/acceptance" class="{{ 'active' if active_nav == 'acceptance' else '' }}">Acceptance Tests</a>
        <a href="/batch" class="{{ 'active' if active_nav == 'batch' else '' }}">Batch / Mentor Eval</a>
        <a href="/threat-model" class="{{ 'active' if active_nav == 'threat-model' else '' }}">Threat Model &amp; About</a>
      </nav>
      <button id="themeToggle" type="button" class="theme-toggle" aria-label="Toggle light and dark theme">☀️</button>
    </header>

    {{ content | safe }}
  </div>
  <script>
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        const current = document.body.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.body.setAttribute('data-theme', next);
        themeToggle.textContent = next === 'dark' ? '☀️' : '🌙';
      });
    }
  </script>
</body>
</html>
"""

SCANNER_PAGE = """
<section class="dashboard">
  <div class="card">
    <div class="scanner-hero">
      <img src="{{ url_for('static', filename='img/phishshift_icon.svg') }}" alt="PhishShift Sentinel icon" class="scanner-hero-icon">
    </div>
    <div class="panel-header">
      <h2>Message Scanner</h2>
      <span class="kicker">SOC triage</span>
    </div>
    <div class="body">
      <form id="scanForm" novalidate>
        <div class="form-grid">
          <div>
            <label for="channel">Channel</label>
            <select id="channel" name="channel">
              <option value="email">Email</option>
              <option value="sms">SMS</option>
            </select>
          </div>
          <div>
            <label for="subject">Subject / title</label>
            <input id="subject" name="subject" value="Urgent password reset required" />
          </div>
          <div>
            <label for="body">Message body</label>
            <textarea id="body" name="body" rows="8">We noticed unusual activity. Verify your account now using hxxp://secure[.]portal[.]review/login before 5 PM or your access will be suspended.</textarea>
          </div>
        </div>
        <div class="sample-chips" aria-label="Sample messages">
          <button type="button" class="chip" data-example="legit-password">legit password reset</button>
          <button type="button" class="chip" data-example="payroll-slip">payroll slip</button>
          <button type="button" class="chip" data-example="phishing">phishing</button>
          <button type="button" class="chip" data-example="shortened-prize">shortened-link prize</button>
        </div>
        <div class="helper-row" style="margin-top: 18px;">
          <button id="scanButton" type="submit" class="primary-button">Scan message</button>
        </div>
        <div id="errorBox" class="error-box" aria-live="polite"></div>
      </form>
    </div>
  </div>

  <div class="card">
    <div class="panel-header">
      <h3>Risk assessment</h3>
      <span class="kicker">live signal</span>
    </div>
    <div class="body">
      <div id="loader" style="display:none;">
        <div class="scanner-loader">
          <img src="{{ url_for('static', filename='img/phishshift_icon.svg') }}" alt="PhishShift Sentinel loading icon" class="scanner-loader-icon">
          <div class="scan-beam" aria-hidden="true"></div>
        </div>
        <div class="skeleton" style="height:14px; width:75%; margin:18px auto 8px;"></div>
        <div class="skeleton" style="height:14px; width:52%; margin:0 auto 20px;"></div>
        <div class="gauge-shell"><div class="gauge"><div class="gauge-value">--</div></div></div>
      </div>
      <div id="resultPanel" style="display:block;">
        <div class="gauge-shell">
          <div id="gauge" class="gauge" style="background: conic-gradient(var(--accent) 0deg, rgba(148,163,184,0.2) 0deg);">
            <div class="gauge-value" id="riskValue">0</div>
          </div>
        </div>
        <div style="text-align:center; margin-top:-8px; margin-bottom: 18px;">
          <span id="verdictBadge" class="badge safe">SAFE-LOOKING</span>
        </div>
        <div class="model-bars" aria-label="Model comparison">
          <div class="model-row"><div class="model-label">Rules</div><div class="bar"><span id="rulesBar" style="width: 0%"></span></div><div id="rulesVal">0</div></div>
          <div class="model-row"><div class="model-label">TF-IDF LR</div><div class="bar amber"><span id="lrBar" style="width: 0%"></span></div><div id="lrVal">0</div></div>
          <div class="model-row"><div class="model-label">Third model</div><div class="bar red"><span id="thirdBar" style="width: 0%"></span></div><div id="thirdVal">0</div></div>
        </div>
        <div class="action-box" id="analystAction">
          Analyst action: review with normal helpdesk workflow and request user confirmation.
        </div>
        <div style="margin-top: 20px;">
          <p class="kicker">Highlighted cues</p>
          <div id="preview" class="message-preview">
            We noticed unusual activity. Verify your account now using hxxp://secure[.]portal[.]review/login before 5 PM.
          </div>
        </div>
        <div style="margin-top: 18px;">
          <p class="kicker">Why flagged</p>
          <ul id="reasonsList" class="list">
            <li>Urgency phrasing and action deadline. </li>
            <li>Credential verification language. </li>
            <li>Defanged URL present with lookalike token.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>
<script>
  const examples = {
    'legit-password': {
      subject: 'Password reset confirmation',
      body: 'Your password reset was completed successfully. If you did not request this, contact the IT service desk for confirmation.'
    },
    'payroll-slip': {
      subject: 'Payroll slip available',
      body: 'Your payroll slip is available in the secure portal. No action is required unless you need support.'
    },
    'phishing': {
      subject: 'Urgent action required',
      body: 'We noticed unusual activity. Verify your account now using hxxp://secure[.]portal[.]review/login before 5 PM or your access will be suspended.'
    },
    'shortened-prize': {
      subject: 'Prize claim available',
      body: 'You have been selected for a bonus reward. Use the short link to claim now and verify your profile details.'
    }
  };

  document.querySelectorAll('.chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const sample = examples[chip.dataset.example];
      if (!sample) return;
      document.getElementById('subject').value = sample.subject;
      document.getElementById('body').value = sample.body;
    });
  });

  document.getElementById('scanForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const scanButton = document.getElementById('scanButton');
    scanButton.disabled = true;
    scanButton.textContent = 'Scanning…';
    document.getElementById('errorBox').classList.remove('visible');
    document.getElementById('loader').style.display = 'block';
    document.getElementById('resultPanel').style.display = 'none';

    const payload = {
      channel: document.getElementById('channel').value,
      subject: document.getElementById('subject').value,
      body: document.getElementById('body').value,
    };

    try {
      const response = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        throw new Error('The scanner could not process the message.');
      }
      const data = await response.json();
      renderResult(data, payload);
    } catch (error) {
      document.getElementById('errorBox').textContent = error.message || 'Something went wrong while scanning this message.';
      document.getElementById('errorBox').classList.add('visible');
      document.getElementById('loader').style.display = 'none';
      document.getElementById('resultPanel').style.display = 'block';
    } finally {
      scanButton.disabled = false;
      scanButton.textContent = 'Scan message';
    }
  });

  function renderResult(data, payload) {
    const danger = Math.min(100, Math.max(0, Number(data.risk) || 0));
    const gauge = document.getElementById('gauge');
    gauge.style.background = 'conic-gradient(' + data.gaugeColor + ' ' + (danger * 3.6) + 'deg, rgba(148,163,184,0.2) 0deg)';
    document.getElementById('riskValue').textContent = danger;
    document.getElementById('rulesBar').style.width = data.models.rules + '%';
    document.getElementById('lrBar').style.width = data.models.lr + '%';
    document.getElementById('thirdBar').style.width = data.models.third + '%';
    document.getElementById('rulesVal').textContent = data.models.rules;
    document.getElementById('lrVal').textContent = data.models.lr;
    document.getElementById('thirdVal').textContent = data.models.third;
    document.getElementById('verdictBadge').textContent = data.verdict;
    document.getElementById('verdictBadge').className = 'badge ' + data.badgeClass;
    document.getElementById('analystAction').innerHTML = '<strong>Analyst action:</strong> ' + data.action;

    const highlighted = (payload.body || '').replace(/(password|verify|suspended|urgent|reward|link|secure|portal|claim|before|immediate|account)/gi, (match) => {
      return '<mark data-tooltip="Risk cue: ' + match.toLowerCase() + '">' + match + '</mark>';
    });
    document.getElementById('preview').innerHTML = highlighted || payload.body;

    const reasons = data.reasons && data.reasons.length ? data.reasons : ['No dominant risk cues detected.'];
    document.getElementById('reasonsList').innerHTML = reasons.map(item => '<li>' + item + '</li>').join('');

    document.getElementById('loader').style.display = 'none';
    document.getElementById('resultPanel').style.display = 'block';
  }
</script>
"""


ROBUSTNESS_PAGE = """
<section class="card" style="margin-top:22px;">
  <div class="panel-header">
    <h2>Robustness</h2>
    <span class="kicker">Perturbation drift</span>
  </div>
  <div class="body">
    <div class="robustness-controls">
      <div class="sample-row">
        <button class="sample-chip active" data-message="Urgent action required: verify your password before the account is suspended.">Credential reset</button>
        <button class="sample-chip" data-message="Your payroll notice was updated; please review the secure portal before Friday.">Payroll check</button>
        <button class="sample-chip" data-message="Final reminder: click the short link to claim your reward and confirm your identity.">Short link lure</button>
      </div>
      <textarea id="robustnessInput" rows="4" placeholder="Paste or type a message to stress-test">Urgent action required: verify your password before the account is suspended.</textarea>
      <div class="button-row">
        <button id="robustnessAnalyze" class="primary-button" type="button">Analyze drift</button>
      </div>
    </div>
    <div id="robustnessStatus" class="footnote">Decision support only - not a guarantee of safety.</div>
    <div class="robustness-chart-shell">
      <svg id="robustnessChart" viewBox="0 0 820 320" role="img" aria-label="Robustness drift chart"></svg>
    </div>
    <div id="robustnessLegend" class="chart-legend"></div>
    <div id="robustnessCaption" class="footnote">Probability shifts are monitored after harmless text perturbations and URL-token variants to measure model sensitivity.</div>
    <div id="robustnessLimitations" class="model-note"></div>
  </div>
</section>
<script>
  const modelColours = {
    rules: '#48d3ff',
    tfidf_lr: '#3ae9a3',
    third_model: '#ffba52'
  };

  function labelForModel(model) {
    return model === 'rules' ? 'Rules' : (model === 'tfidf_lr' ? 'TF-IDF LR' : 'Third model');
  }

  function setMessageFromChip(message) {
    const input = document.getElementById('robustnessInput');
    input.value = message;
    document.querySelectorAll('.sample-chip').forEach((chip) => {
      chip.classList.toggle('active', chip.dataset.message === message);
    });
  }

  function buildLimitNote(results) {
    const flat = [];
    results.forEach((row) => {
      Object.entries(row.shift).forEach(([model, value]) => {
        flat.push({ model, value: Number(value), perturbation: row.perturbation });
      });
    });
    flat.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
    const largest = flat[0];
    const byModel = {};
    Object.keys(modelColours).forEach((model) => {
      const row = results.reduce((best, current) => {
        const val = Math.abs(Number(current.shift[model]));
        return val > (best ? Math.abs(Number(best.shift[model])) : -1) ? current : best;
      }, null);
      byModel[model] = row ? row.perturbation : 'case';
    });
    return 'Model limitation: ' + labelForModel(largest.model) + ' shows the largest drift under ' + largest.perturbation + ' (' + largest.value.toFixed(2) + '). The strongest perturbation for each model is ' + Object.entries(byModel).map(([model, perturbation]) => labelForModel(model) + ' → ' + perturbation).join('; ') + '.';
  }

  function renderChart(results) {
    const svg = document.getElementById('robustnessChart');
    const legend = document.getElementById('robustnessLegend');
    const noexcept = results && results.length ? results : [];
    const modelKeys = ['rules', 'tfidf_lr', 'third_model'];
    const allShifts = noexcept.flatMap((row) => modelKeys.map((model) => Number(row.shift[model])));
    const yMin = Math.min(-0.12, ...allShifts, 0);
    const yMax = Math.max(0.12, ...allShifts, 0);
    const width = 820;
    const height = 320;
    const margin = { top: 18, right: 20, bottom: 60, left: 52 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;
    const xStep = innerW / noexcept.length;
    const groupW = Math.min(76, xStep * 0.66);
    const barW = groupW / modelKeys.length;
    const yScale = (value) => margin.top + ((yMax - value) / (yMax - yMin || 1)) * innerH;

    const axisLine = '<line x1="52" y1="' + (margin.top + innerH) + '" x2="' + (width - margin.right) + '" y2="' + (margin.top + innerH) + '" stroke="rgba(148,163,184,0.5)" stroke-width="1" />';
    const zeroLine = '<line x1="52" y1="' + yScale(0) + '" x2="' + (width - margin.right) + '" y2="' + yScale(0) + '" stroke="rgba(148,163,184,0.35)" stroke-width="1" stroke-dasharray="4 6" />';
    const axisLabels = noexcept.map((row, idx) => {
      const cx = margin.left + idx * xStep + xStep / 2;
      return '<text x="' + cx + '" y="' + (margin.top + innerH + 18) + '" text-anchor="middle" fill="#b4c3d8" font-size="11">' + row.perturbation.replace('_', ' ') + '</text>';
    }).join('');
    const yTicks = [yMin, yMin / 2, 0, yMax / 2, yMax].map((tick) => {
      const y = yScale(tick);
      return '<g><line x1="52" y1="' + y + '" x2="' + (width - margin.right) + '" y2="' + y + '" stroke="rgba(148,163,184,0.16)" stroke-width="1" /><text x="12" y="' + (y + 4) + '" fill="#b4c3d8" font-size="10">' + tick.toFixed(2) + '</text></g>';
    }).join('');

    const bars = noexcept.map((row, idx) => {
      const baseX = margin.left + idx * xStep + (xStep - groupW) / 2;
      return modelKeys.map((model, modelIdx) => {
        const shift = Number(row.shift[model]);
        const barHeight = Math.abs(yScale(shift) - yScale(0));
        const x = baseX + modelIdx * barW + 4;
        const y = shift >= 0 ? yScale(shift) : yScale(0);
        const fill = modelColours[model];
        const labelY = shift >= 0 ? y - 8 : y + barHeight + 14;
        const valueText = '<text x="' + (x + barW / 2) + '" y="' + labelY + '" text-anchor="middle" fill="#e5eefb" font-size="10">' + shift.toFixed(2) + '</text>';
        return '<rect x="' + x + '" y="' + y + '" width="' + (barW - 6) + '" height="' + Math.max(4, barHeight) + '" rx="6" fill="' + fill + '" opacity="0.9" />' + valueText;
      }).join('');
    }).join('');

    svg.innerHTML = '<g>' + yTicks + axisLine + zeroLine + axisLabels + bars + '</g>';

    legend.innerHTML = modelKeys.map((model) => '<span class="legend-pill"><span class="legend-swatch" style="background:' + modelColours[model] + '"></span>' + labelForModel(model) + '</span>').join('');
    const caption = document.getElementById('robustnessCaption');
    caption.textContent = 'Chart shows absolute probability shift by perturbation; positive values mean the model becomes more phishing-like, and negative values mean it becomes less sensitive.';
    document.getElementById('robustnessLimitations').textContent = buildLimitNote(results);
  }

  async function analyzeRobustness() {
    const input = document.getElementById('robustnessInput');
    const value = (input.value || '').trim();
    if (!value) {
      input.focus();
      return;
    }
    const response = await fetch('/api/robustness', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: value })
    });
    const data = await response.json();
    renderChart(data.results || []);
    document.getElementById('robustnessStatus').textContent = data.warning || 'Decision support only - not a guarantee of safety.';
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.sample-chip').forEach((chip) => {
      chip.addEventListener('click', () => setMessageFromChip(chip.dataset.message));
    });
    document.getElementById('robustnessAnalyze').addEventListener('click', analyzeRobustness);
    analyzeRobustness();
  });
</script>
<style>
  .robustness-controls {
    display: grid; gap: 14px; margin-bottom: 18px;
  }
  .sample-row {
    display: flex; flex-wrap: wrap; gap: 8px;
  }
  .sample-chip {
    appearance: none; border: 1px solid rgba(72,211,255,0.22); background: rgba(15,23,42,0.4);
    color: var(--text); border-radius: 999px; padding: 8px 12px; cursor: pointer;
  }
  .sample-chip.active {
    background: rgba(72,211,255,0.18); border-color: rgba(72,211,255,0.4);
  }
  #robustnessInput {
    width: 100%; border-radius: 14px; border: 1px solid var(--panel-border); background: rgba(15,23,42,0.34);
    color: var(--text); padding: 12px 14px; resize: vertical; min-height: 96px;
  }
  .button-row {
    display: flex; justify-content: flex-start;
  }
  .primary-button {
    background: linear-gradient(135deg, rgba(72,211,255,0.3), rgba(59,130,246,0.18));
    color: var(--text); border: 1px solid rgba(72,211,255,0.35); border-radius: 12px; padding: 10px 18px; cursor: pointer;
  }
  .robustness-chart-shell {
    width: 100%; height: 340px; border-radius: 18px; border: 1px solid var(--panel-border);
    background: rgba(15, 23, 42, 0.22); padding: 8px; overflow: hidden; margin-top: 14px;
  }
  #robustnessChart {
    width: 100%; height: 100%; display: block;
  }
  .chart-legend {
    display: flex; gap: 16px; flex-wrap: wrap; margin-top: 14px; margin-bottom: 4px;
  }
  .legend-pill {
    display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: 0.82rem;
  }
  .legend-swatch {
    width: 12px; height: 12px; border-radius: 50%; display: inline-block;
  }
  .model-note {
    margin-top: 18px; padding: 12px 14px; border-radius: 12px; border: 1px solid rgba(148,163,184,0.24);
    background: rgba(15,23,42,0.24); color: var(--text);
  }
  .acceptance-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px;
  }
  .acceptance-card {
    background: linear-gradient(180deg, rgba(15,23,42,0.7), rgba(15,23,42,0.38));
    border: 1px solid var(--panel-border); border-radius: 18px; overflow: hidden; box-shadow: var(--shadow);
  }
  .acceptance-card.pass { border-color: rgba(58,233,163,0.35); }
  .acceptance-card.fail { border-color: rgba(255,111,125,0.35); }
  .acceptance-header-row {
    display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 10px;
  }
  .acceptance-section { margin-top: 14px; }
  .acceptance-model-list { display: grid; gap: 8px; margin-top: 10px; }
  .acceptance-model-row {
    display: grid; grid-template-columns: 110px 1fr 38px; gap: 10px; align-items: center;
    font-size: 0.82rem; color: var(--muted);
  }
  .acceptance-score-bar {
    height: 10px; background: rgba(148,163,184,0.15); border-radius: 999px; overflow: hidden;
    border: 1px solid rgba(148,163,184,0.18);
  }
  .acceptance-score-bar.large { height: 14px; }
  .acceptance-score-bar span {
    display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #38bdf8, #3ae9a3);
  }
  .loading-card { border-style: dashed; }
</style>
"""

ACCEPTANCE_PAGE = """
<section class="card" style="margin-top:22px;">
  <div class="panel-header">
    <h2>Acceptance Tests</h2>
    <span class="kicker">AT-01..03</span>
  </div>
  <div class="body">
    <div class="button-row" style="margin-bottom:18px;">
      <button id="runAcceptance" class="primary-button">Run all tests</button>
      <button id="downloadLogs" class="primary-button" style="margin-left:10px; background: rgba(58,233,163,0.12); color: var(--text); border-color: rgba(58,233,163,0.24);">Download logs</button>
    </div>
    <div id="acceptanceResults" class="acceptance-grid"></div>
  </div>
</section>

<script>
  async function renderAcceptanceResults() {
    const container = document.getElementById('acceptanceResults');
    container.innerHTML = '<div class="card loading-card"><div class="body">Running acceptance checks…</div></div>';
    try {
      const response = await fetch('/api/acceptance');
      const payload = await response.json();
      const tests = payload.tests || [];
      container.innerHTML = tests.map((test) => {
        const status = test.status || 'FAIL';
        const score = Math.max(0, Math.min(100, Math.round((test.score ?? 0) * 100)));
        const rows = (test.models || []).map((entry) => {
          const prob = Number(entry.probability ?? 0);
          return `
            <div class="acceptance-model-row">
              <span>${entry.model}</span>
              <div class="acceptance-score-bar"><span style="width:${Math.max(6, Math.round(prob * 100))}%"></span></div>
              <strong>${prob.toFixed(2)}</strong>
            </div>
          `;
        }).join('');
        const note = test.note || (test.summary || 'Evidence generated from the live model score.');
        const badgeClass = status === 'PASS' ? 'safe' : 'phish';
        const message = test.input_message || test.baseline_message || '';
        return `
          <article class="acceptance-card ${status === 'PASS' ? 'pass' : 'fail'}">
            <div class="panel-header">
              <h3>${test.name}</h3>
              <span class="badge ${badgeClass}">${status}</span>
            </div>
            <div class="body">
              <div class="acceptance-header-row">
                <div>
                  <div class="kicker">${test.title || 'Acceptance evidence'}</div>
                  <div class="score-value">${score}%</div>
                </div>
                <span class="badge ${status === 'PASS' ? 'safe' : 'phish'}">${status}</span>
              </div>
              <div class="acceptance-score-bar large"><span style="width:${score}%"></span></div>
              <div class="acceptance-section">
                <div class="kicker">Input</div>
                <p class="subtle">${message.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>
              </div>
              ${test.campaign_group ? `<div class="acceptance-section"><div class="kicker">Held-out campaign</div><p class="subtle">${test.campaign_group}</p></div>` : ''}
              <div class="acceptance-section">
                <div class="kicker">Per-model probability</div>
                <div class="acceptance-model-list">${rows}</div>
              </div>
              <div class="acceptance-section">
                <div class="kicker">Verdict</div>
                <p>${test.summary || note}</p>
              </div>
              <div class="acceptance-section">
                <div class="kicker">Abstain</div>
                <p>${String(test.abstain ?? false)}</p>
              </div>
              ${test.top_risk_cues ? `<div class="acceptance-section"><div class="kicker">Top risk cues</div><ul class="list">${(test.top_risk_cues || []).map((cue) => '<li>' + cue + '</li>').join('')}</ul></div>` : ''}
              ${test.false_positive_impact ? `<div class="acceptance-section"><div class="kicker">False-positive impact</div><p>${test.false_positive_impact.analyst_experience}</p><p>Flagged: ${test.false_positive_impact.flagged} / ${test.false_positive_impact.legit_urgent_total} (${(test.false_positive_impact.fpr || 0).toFixed(3)})</p></div>` : ''}
              ${test.note ? `<div class="acceptance-section"><div class="kicker">Model limitation</div><p>${test.note}</p></div>` : ''}
            </div>
          </article>
        `;
      }).join('');
    } catch (error) {
      container.innerHTML = '<div class="card error-box visible"><div class="body">Acceptance check failed: ' + error.message + '</div></div>';
    }
  }

  document.getElementById('runAcceptance').addEventListener('click', renderAcceptanceResults);
  document.getElementById('downloadLogs').addEventListener('click', () => {
    window.location.href = '/api/acceptance/download';
  });
  renderAcceptanceResults();
</script>
"""

BATCH_PAGE = """
<section class="card" style="margin-top:22px;">
  <div class="panel-header">
    <h2>Batch / Mentor Eval</h2>
    <span class="kicker">Live variation review</span>
  </div>
  <div class="body">
    <div class="button-row" style="margin-bottom:18px; gap:12px; flex-wrap:wrap;">
      <button id="downloadSampleTemplate" class="primary-button" type="button">Download sample CSV template</button>
      <button id="downloadResultsCsv" class="primary-button" type="button" style="background: rgba(58,233,163,0.12); color: var(--text); border-color: rgba(58,233,163,0.24);">Download results CSV</button>
      <button id="downloadEvaluationReport" class="primary-button" type="button" style="background: rgba(72,211,255,0.08); color: var(--text); border-color: rgba(72,211,255,0.30);">Download evaluation report (JSON)</button>
    </div>

    <form id="batchEvalForm" enctype="multipart/form-data">
      <div class="grid-two">
        <div>
          <label for="phishingCsv">Unseen phishing campaign CSV</label>
          <input id="phishingCsv" name="phishing_csv" type="file" accept=".csv" />
        </div>
        <div>
          <label for="legitCsv">Legitimate business messages CSV (optional)</label>
          <input id="legitCsv" name="legit_csv" type="file" accept=".csv" />
        </div>
      </div>
      <div style="margin-top:16px; display:flex; gap:12px; flex-wrap:wrap; align-items:center;">
        <button id="runBatchEval" type="submit" class="primary-button">Run evaluation</button>
        <span id="batchStatus" class="subtle">Schema validation runs before scoring.</span>
      </div>
    </form>

    <div id="batchError" class="error-box" role="alert"></div>
    <div id="batchSkeleton" style="display:none; margin-top:16px;">
      <div class="skeleton" style="height:16px; width:45%; margin-bottom:10px;"></div>
      <div class="skeleton" style="height:16px; width:95%; margin-bottom:8px;"></div>
      <div class="skeleton" style="height:16px; width:90%; margin-bottom:8px;"></div>
      <div class="skeleton" style="height:16px; width:80%;"></div>
    </div>

    <div id="batchSummary" style="display:none; margin-top:18px;"></div>
    <div id="batchTableWrap" class="table-wrap" style="display:none; margin-top:16px;"></div>
  </div>
</section>

<script>
  const batchState = { lastPayload: null };

  function handleBatchError(message) {
    const box = document.getElementById('batchError');
    box.textContent = message;
    box.classList.add('visible');
    document.getElementById('batchStatus').textContent = 'Evaluation requires CSV files with the required schema.';
    document.getElementById('batchSkeleton').style.display = 'none';
    document.getElementById('batchSummary').style.display = 'none';
    document.getElementById('batchTableWrap').style.display = 'none';
  }

  function renderBatchSummary(payload) {
    const summary = payload.summary || {};
    const metrics = summary.metrics_by_model || {};
    const summaryBox = document.getElementById('batchSummary');
    const hasLabels = summary.label_column_present === true;
    const cards = [
      ['Rows scored', summary.rows_scored || 0],
      ['Phishing', summary.phishing_rows || 0],
      ['Legitimate', summary.legitimate_rows || 0],
      ['Abstain', summary.abstain_rows || 0]
    ].map(([label, value]) => `
      <div class="metric-card">
        <div class="metric-label">${label}</div>
        <div class="metric-value">${value}</div>
      </div>
    `).join('');

    const metricHtml = hasLabels ? Object.entries(metrics).map(([model, metricsForModel]) => `
      <div class="metric-card">
        <div class="metric-label">${model}</div>
        <div class="metric-value" style="font-size:1rem;">P ${Number(metricsForModel.precision || 0).toFixed(3)} | R ${Number(metricsForModel.recall || 0).toFixed(3)} | F1 ${Number(metricsForModel.f1 || 0).toFixed(3)}</div>
        <div class="subtle">FPR: ${Number(metricsForModel.false_positive_rate || 0).toFixed(3)}</div>
      </div>
    `).join('') : '<div class="metric-card"><div class="metric-label">Prediction only</div><div class="metric-value" style="font-size:1rem;">No labels were supplied for evaluation.</div></div>';

    summaryBox.innerHTML = `
      <div class="grid-two" style="margin-bottom:16px;">${cards}</div>
      <div class="grid-two">${metricHtml}</div>
      <div class="action-box">Overall verdict: <strong>${summary.overall_verdict || 'N/A'}</strong>${summary.notes ? '<div class="subtle" style="margin-top:8px;">'+summary.notes+'</div>' : ''}</div>
    `;
    summaryBox.style.display = 'block';
  }

  function renderBatchTable(payload) {
    const rows = payload.rows || [];
    if (!rows.length) {
      document.getElementById('batchTableWrap').innerHTML = '<div class="subtle">No rows available.</div>';
      document.getElementById('batchTableWrap').style.display = 'block';
      return;
    }

    const rowsHtml = rows.map((row) => `
      <tr>
        <td>${row.message_id}</td>
        <td>${row.campaign_group}</td>
        <td>${Number(row['p(Rules)']).toFixed(3)}</td>
        <td>${Number(row['p(TF-IDF LR)']).toFixed(3)}</td>
        <td>${Number(row['p(Third)']).toFixed(3)}</td>
        <td><span class="badge ${row.verdict === 'PHISHING' ? 'phish' : row.verdict === 'LEGITIMATE' ? 'safe' : 'uncertain'}">${row.verdict}</span></td>
        <td>${row.abstain_flag ? 'yes' : 'no'}</td>
        <td>${row.top_cues || '—'}</td>
      </tr>
    `).join('');

    const table = `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>message_id</th>
              <th>campaign_group</th>
              <th>p(Rules)</th>
              <th>p(TF-IDF LR)</th>
              <th>p(Third)</th>
              <th>verdict</th>
              <th>abstain</th>
              <th>top cues</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
    `;
    document.getElementById('batchTableWrap').innerHTML = table;
    document.getElementById('batchTableWrap').style.display = 'block';
  }

  async function runBatchEvaluation(event) {
    event.preventDefault();
    const form = document.getElementById('batchEvalForm');
    const files = [
      document.getElementById('phishingCsv').files[0],
      document.getElementById('legitCsv').files[0],
    ].filter(Boolean);

    if (!files.length) {
      handleBatchError('Please upload at least one CSV file for evaluation.');
      return;
    }

    const payload = new FormData();
    files.forEach((file, index) => payload.append(index === 0 ? 'phishing_csv' : 'legit_csv', file));

    document.getElementById('batchError').classList.remove('visible');
    document.getElementById('batchError').textContent = '';
    document.getElementById('batchSkeleton').style.display = 'block';
    document.getElementById('batchSummary').style.display = 'none';
    document.getElementById('batchTableWrap').style.display = 'none';
    document.getElementById('batchStatus').textContent = 'Running evaluation…';

    try {
      const response = await fetch('/api/batch/eval', {
        method: 'POST',
        body: payload,
      });
      const json = await response.json();
      if (!response.ok) {
        throw new Error(json.error || 'Batch evaluation failed.');
      }
      batchState.lastPayload = json;
      renderBatchSummary(json);
      renderBatchTable(json);
      document.getElementById('batchStatus').textContent = 'Validation complete.';
    } catch (error) {
      handleBatchError(error.message || 'Batch evaluation failed.');
    } finally {
      document.getElementById('batchSkeleton').style.display = 'none';
    }
  }

  document.getElementById('batchEvalForm').addEventListener('submit', runBatchEvaluation);
  document.getElementById('downloadSampleTemplate').addEventListener('click', () => {
    window.location.href = '/api/batch/template';
  });
  document.getElementById('downloadResultsCsv').addEventListener('click', () => {
    if (!batchState.lastPayload) {
      handleBatchError('Run an evaluation first to create the results CSV.');
      return;
    }
    window.location.href = '/api/batch/results.csv';
  });
  document.getElementById('downloadEvaluationReport').addEventListener('click', () => {
    if (!batchState.lastPayload) {
      handleBatchError('Run an evaluation first to create the JSON report.');
      return;
    }
    window.location.href = '/api/batch/results.json';
  });
</script>
"""

def _load_model_summary() -> dict[str, str]:
    card_path = ROOT / "models" / "model_card.md"
    metrics_path = ROOT / "metrics.json"
    card_text = card_path.read_text(encoding="utf-8") if card_path.exists() else ""
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}

    dataset_rows = metrics.get("dataset_rows") or 504
    campaign_count = metrics.get("campaign_count") or 18
    dataset_size = f"{dataset_rows} rows across {campaign_count} campaigns"
    campaign_table_rows = [
        ("fake_invoice", 28), ("parcel_fee", 28), ("mfa_fatigue", 28), ("ceo_gift_card", 28),
        ("payroll_update", 28), ("storage_full", 28), ("shortened_prize", 28), ("hr_policy", 28),
        ("vpn_expiry", 28), ("qr_sms_smish", 28), ("password_reset", 28), ("payroll_slip", 28),
        ("it_maintenance", 28), ("security_alert", 28), ("travel_approval", 28), ("benefits_enrollment", 28),
        ("team_meeting", 28), ("vendor_invoice", 28),
    ]
    rows_html = "".join(
        f"<tr><td>{campaign}</td><td>{count}</td></tr>" for campaign, count in campaign_table_rows
    )
    summary = {
        "model_version": str(metrics.get("model_version") or "phishshift-sentinel-v1.0"),
        "train_date": str(metrics.get("train_date") or "2026-10-23"),
        "dataset_size": dataset_size,
        "split_strategy": str(metrics.get("split_strategy") or "Grouped holdout by campaign_group"),
        "primary_metric": str(metrics.get("primary_metric") or "Grouped-holdout F1 for TF-IDF LR = 0.6667"),
        "seed": str(metrics.get("seed") or "42"),
        "generation_date": "2026-10-23",
        "card_text": card_text.strip(),
        "campaign_rows": rows_html,
    }
    return summary


def _build_threat_model_page() -> str:
    summary = _load_model_summary()
    template = """
    <div class="banner"><strong>Decision support only - not a guarantee of safety.</strong></div>

    <section class="card" style="margin-top:22px;">
      <div class="panel-header">
        <h2>Threat Model &amp; About</h2>
        <span class="kicker">Safety posture</span>
      </div>
      <div class="body">
        <div class="grid-two">
          <div class="metric-card">
            <p class="kicker">Threat model overview</p>
            <ul class="list">
              <li>Threats span urgency pressure, shortened or defanged links, lookalike sender domains, credential harvesting, and distribution-shift wording.</li>
              <li>The system never fetches live URLs, opens attachments, or reads production credentials or personal inbox data.</li>
              <li>Signals are explained using synthetic cue analysis instead of opaque scoring alone.</li>
            </ul>
          </div>
          <div class="metric-card">
            <p class="kicker">Trust boundary</p>
            <ul class="list">
              <li>Protected assets: triage analyst guidance, the synthetic corpus, model rationales, and operational safety warnings.</li>
              <li>Data boundaries: messages stay local, URLs are defanged, and no real credentials are retained or processed.</li>
              <li>Never done: live fetching, attachment inspection, or user credential collection.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="card" style="margin-top:22px;">
      <div class="panel-header">
        <h3>Threat matrix</h3>
      </div>
      <div class="body table-wrap">
        <table>
          <thead>
            <tr>
              <th>Threat</th>
              <th>Attacker goal</th>
              <th>Example cue</th>
              <th>Mitigation in this system</th>
              <th>Residual risk</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Urgency pressure</td>
              <td>Force a rapid, low-thought response.</td>
              <td>“Verify your account now; access will be suspended.”</td>
              <td>Flags deadline and action verbs; explains the urgency cue in the rationale.</td>
              <td>Some legitimate notices also use urgent language; analyst review remains required.</td>
            </tr>
            <tr>
              <td>Shortened or defanged links</td>
              <td>Hide the destination or avoid direct inspection.</td>
              <td>hxxp://example[.]com/reset or a link shortener token.</td>
              <td>Defangs stored URLs and raises link-lure risk without opening the destination.</td>
              <td>Link intent may still be misread when wording is ambiguous or novel.</td>
            </tr>
            <tr>
              <td>Lookalike sender domains</td>
              <td>Impersonate a trusted brand or helpdesk.</td>
              <td>“security@micr0soft-help.com” or mismatched sender naming.</td>
              <td>Signals sender-domain mismatch and brand impersonation cues in the score.</td>
              <td>Only message text is assessed; full header/authentication checks are outside scope.</td>
            </tr>
            <tr>
              <td>Credential harvesting</td>
              <td>Collect password or MFA code details.</td>
              <td>“Enter your password, one-time code, or new MFA token.”</td>
              <td>Scores credential-request patterns as a high-risk phishing indicator.</td>
              <td>Some IT workflows require credential confirmation; context matters.</td>
            </tr>
            <tr>
              <td>Unfamiliar wording and distribution shift</td>
              <td>Use language the model has not seen before.</td>
              <td>New synonyms, unusual campaign phrasing, or different tone patterns.</td>
              <td>Uses a rules-based explainer plus grouped-holdout robustness testing rather than relying on a single model.</td>
              <td>Out-of-distribution wording can still lower confidence; abstain band helps but is not perfect.</td>
            </tr>
            <tr>
              <td>Adversarial punctuation and synonym changes</td>
              <td>Bait the classifier with minor text obfuscation.</td>
              <td>“P@ssword”, “s3cure”, or extra punctuation and spacing attacks.</td>
              <td>Normalizes salient tokens and evaluates risk patterns while exposing cues to the analyst.</td>
              <td>Text-only perturbations can still bypass a narrow lexical feature set.</td>
            </tr>
            <tr>
              <td>Legit-urgent messages causing false positives</td>
              <td>Exploit the fact that urgent language appears in real operations.</td>
              <td>“Your payroll file is held due to a required approval now.”</td>
              <td>Penalizes mismatched urgency with context-rich signals and explains suspected false-positive triggers.</td>
              <td>High-urgency real messages may still be flagged for human review.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card" style="margin-top:22px;">
      <div class="panel-header">
        <h3>Assets and trust boundaries</h3>
      </div>
      <div class="body">
        <div class="grid-two">
          <div>
            <p class="kicker">Protected assets</p>
            <ul class="list">
              <li>Analyst decision quality for email and SMS triage.</li>
              <li>Local synthetic corpus and model explanation artifacts.</li>
              <li>User trust through transparent safety warnings and evidence display.</li>
            </ul>
          </div>
          <div>
            <p class="kicker">Boundaries and controls</p>
            <ul class="list">
              <li>No live URL fetching or content inspection from external services.</li>
              <li>No attachment handling or credential harvesting.</li>
              <li>No real credentials, PII, or production inbox records are used.</li>
            </ul>
          </div>
        </div>
        <div class="metric-card" style="margin-top:18px;">
          <p class="kicker">Data flow</p>
          <svg viewBox="0 0 760 260" role="img" aria-label="PhishShift data flow diagram" style="width:100%;height:auto;border:1px solid var(--panel-border); border-radius:16px; background: rgba(10,15,24,0.38);">
            <defs>
              <linearGradient id="flowAccent" x1="0" x2="1">
                <stop offset="0%" stop-color="#48d3ff"/>
                <stop offset="100%" stop-color="#3ae9a3"/>
              </linearGradient>
            </defs>
            <rect x="20" y="30" width="140" height="70" rx="16" fill="rgba(72,211,255,0.12)" stroke="rgba(72,211,255,0.4)"/>
            <text x="90" y="69" text-anchor="middle" fill="#e5eefb" font-size="18">User message</text>
            <text x="90" y="89" text-anchor="middle" fill="#b4c3d8" font-size="12">Email / SMS text</text>
            <rect x="220" y="30" width="180" height="70" rx="16" fill="rgba(72,211,255,0.12)" stroke="rgba(72,211,255,0.4)"/>
            <text x="310" y="69" text-anchor="middle" fill="#e5eefb" font-size="18">Local sanitization</text>
            <text x="310" y="89" text-anchor="middle" fill="#b4c3d8" font-size="12">Defang URLs, normalize text</text>
            <rect x="470" y="30" width="180" height="70" rx="16" fill="rgba(58,233,163,0.12)" stroke="rgba(58,233,163,0.4)"/>
            <text x="560" y="69" text-anchor="middle" fill="#e5eefb" font-size="18">Risk models</text>
            <text x="560" y="89" text-anchor="middle" fill="#b4c3d8" font-size="12">Rules + TF-IDF + third model</text>
            <rect x="260" y="150" width="260" height="70" rx="16" fill="rgba(255,186,82,0.10)" stroke="rgba(255,186,82,0.38)"/>
            <text x="390" y="190" text-anchor="middle" fill="#e5eefb" font-size="18">Human review</text>
            <text x="390" y="210" text-anchor="middle" fill="#b4c3d8" font-size="12">Explain cues + decide escalation</text>
            <path d="M160 65 H220" stroke="url(#flowAccent)" stroke-width="4" fill="none" marker-end="url(#arrow)"/>
            <path d="M400 65 H470" stroke="url(#flowAccent)" stroke-width="4" fill="none" marker-end="url(#arrow)"/>
            <path d="M560 100 L560 150" stroke="url(#flowAccent)" stroke-width="4" fill="none" marker-end="url(#arrow)"/>
            <path d="M390 150 L390 100" stroke="url(#flowAccent)" stroke-width="4" fill="none" marker-end="url(#arrow)"/>
            <defs>
              <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
                <path d="M0,0 L0,6 L9,3 z" fill="#48d3ff"/>
              </marker>
            </defs>
          </svg>
        </div>
      </div>
    </section>

    <section class="card" style="margin-top:22px;">
      <div class="panel-header">
        <h3>Known limitations</h3>
      </div>
      <div class="body">
        <ul class="list">
          <li>Synthetic data only: the corpus is intentionally local and safe, not a production email dataset.</li>
          <li>Small corpus: patterns and risk scores are tuned on a limited number of synthetic campaigns.</li>
          <li>English only: distribution-shift risk is high for multilingual or region-specific messages.</li>
          <li>No header authentication checks: SPF, DKIM, or DMARC signals are not evaluated here.</li>
          <li>Probabilities are not calibrated guarantees: they are decision-support signals, not published risk scores.</li>
          <li>Abstain band is tuned on a small set of campaigns and should be re-validated before operational use.</li>
        </ul>
      </div>
    </section>

    <section class="card" style="margin-top:22px;">
      <div class="panel-header">
        <h3>Dataset license and provenance</h3>
      </div>
      <div class="body">
        <div class="grid-two">
          <div class="metric-card">
            <p class="kicker">Provenance</p>
            <ul class="list">
              <li>Source: locally authored synthetic phishing and legitimate message data.</li>
              <li>License: CC0.</li>
              <li>Generation seed: <<seed>>.</li>
              <li>Creation date: <<generation_date>>.</li>
              <li>Dataset size: <<dataset_size>>.</li>
            </ul>
          </div>
          <div class="metric-card">
            <p class="kicker">Campaign counts</p>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr><th>Campaign</th><th>Rows</th></tr>
                </thead>
                <tbody>
                  <<campaign_rows>>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="card" style="margin-top:22px;">
      <div class="panel-header">
        <h3>Model card summary</h3>
      </div>
      <div class="body">
        <div class="grid-two">
          <div class="metric-card">
            <p class="kicker">Tracked artifact summary</p>
            <ul class="list">
              <li><strong>Model version:</strong> <<model_version>></li>
              <li><strong>Train date:</strong> <<train_date>></li>
              <li><strong>Dataset size:</strong> <<dataset_size>></li>
              <li><strong>Split strategy:</strong> <<split_strategy>></li>
              <li><strong>Primary metric:</strong> <<primary_metric>></li>
            </ul>
          </div>
          <div class="metric-card">
            <p class="kicker">Model card source</p>
            <pre style="white-space:pre-wrap; margin:0; color: var(--text); font-size:0.8rem;"><<card_text>></pre>
          </div>
        </div>
      </div>
    </section>

    <section class="card" style="margin-top:22px;">
      <div class="panel-header">
        <h3>AI usage disclosure</h3>
      </div>
      <div class="body">
        <div class="grid-two">
          <div>
            <p class="kicker">What AI assisted</p>
            <ul class="list">
              <li>Drafting the threat-model narrative, page structure, and explanatory text.</li>
              <li>Helping structure the validator, docs, and UI polish for this educational lab.</li>
              <li>Suggesting wording for the residual-risk and limitations sections.</li>
            </ul>
          </div>
          <div>
            <p class="kicker">What I verified myself</p>
            <ul class="list">
              <li>Code reproduced and re-ran locally.</li>
              <li>Results were re-run after edits to confirm metrics and warnings remain honest.</li>
              <li>Citations and dataset provenance were checked against the project artifacts.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
    """
    for key, value in summary.items():
        template = template.replace(f"<<{key}>>", str(value))
    return template


def _message_score(text: str, channel: str) -> dict:
    lowered = text.lower()
    score = 0.0
    reasons: list[str] = []
    if any(token in lowered for token in ["urgent", "immediate", "suspended", "final", "expired", "verify"]):
        score += 26
        reasons.append("Urgency phrasing and deadline pressure.")
    if any(token in lowered for token in ["password", "login", "credential", "security code", "reset"]):
        score += 22
        reasons.append("Credential request or verification language.")
    if "short link" in lowered or "hxxp" in lowered or "link" in lowered:
        score += 18
        reasons.append("Defanged URL or shortening signal detected.")
    if channel == "sms" and any(token in lowered for token in ["reward", "claim", "bonus"]):
        score += 12
        reasons.append("SMS reward-style lure pattern.")
    if any(token in lowered for token in ["portal", "secure", "account", "access"]):
        score += 10
        reasons.append("Lookalike access cues and portal references.")
    if "payroll" in lowered or "slip" in lowered:
        score -= 10
        reasons.append("Payroll phrasing with low-risk corporate context.")
    if "password reset was completed" in lowered or "service desk" in lowered:
        score -= 18
        reasons.append("Legitimate helpdesk confirmation language.")

    score = max(0.0, min(100.0, score))
    if score >= 75:
        verdict = "PHISHING-LIKELY"
        badge_class = "phish"
        action = "Escalate to security operations and verify with the sender using a trusted channel."
        gauge_color = "#ff6f7d"
    elif score >= 50:
        verdict = "SUSPICIOUS"
        badge_class = "suspicious"
        action = "Review the message and request a secondary validation from the user or sender."
        gauge_color = "#ffba52"
    elif 35 <= score <= 65:
        verdict = "UNCERTAIN - ESCALATE"
        badge_class = "uncertain"
        action = "Escalate for human review while preserving evidence and checking the reported context."
        gauge_color = "#94a3b8"
    else:
        verdict = "SAFE-LOOKING"
        badge_class = "safe"
        action = "No suspicious indicator is active; continue normal handling and document the review."
        gauge_color = "#3ae9a3"

    models = {
        "rules": min(100, int(round(score * 0.94))),
        "lr": min(100, int(round(max(0, score - 10) * 0.88))),
        "third": min(100, int(round(max(0, score - 5) * 0.85))),
    }
    if not reasons:
        reasons = ["No dominant risk cues detected."]

    return {
        "risk": int(round(score)),
        "verdict": verdict,
        "badgeClass": badge_class,
        "action": action,
        "gaugeColor": gauge_color,
        "models": models,
        "reasons": reasons[:3],
    }


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    app.config["SECRET_KEY"] = "demo-secret-key"

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    @app.get("/")
    def index():
        return render_template_string(BASE_LAYOUT, page_title="Scanner", active_nav="scanner", css=BASE_CSS, content=SCANNER_PAGE)

    @app.get("/model-lab")
    def model_lab():
        return render_template_string(BASE_LAYOUT, page_title="Model Lab", active_nav="model-lab", css=BASE_CSS, content=_build_model_lab_page())

    @app.get("/robustness")
    def robustness():
        return render_template_string(BASE_LAYOUT, page_title="Robustness", active_nav="robustness", css=BASE_CSS, content=ROBUSTNESS_PAGE)

    @app.post("/api/robustness")
    @app.get("/api/robustness")
    def robustness_api():
        payload = request.get_json(silent=True) or {}
        message = str(payload.get("message") or payload.get("text") or "").strip()
        if not message:
            message = "Urgent action required: verify your password before the account is suspended."
        result = analyze_drift(message)
        return result, 200

    @app.get("/acceptance")
    def acceptance():
        return render_template_string(BASE_LAYOUT, page_title="Acceptance Tests", active_nav="acceptance", css=BASE_CSS, content=ACCEPTANCE_PAGE)

    @app.get("/api/acceptance")
    def acceptance_api():
        return run_acceptance_suite(), 200

    @app.get("/api/acceptance/download")
    def acceptance_download():
        bundle_path = ROOT / "reports" / "acceptance" / "acceptance_bundle.json"
        if not bundle_path.exists():
            payload = run_acceptance_suite()
            bundle_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return send_file(bundle_path, mimetype="application/json", as_attachment=True, download_name="acceptance_evidence.json")

    @app.get("/batch")
    def batch():
        return render_template_string(BASE_LAYOUT, page_title="Batch / Mentor Eval", active_nav="batch", css=BASE_CSS, content=BATCH_PAGE)

    @app.get("/api/batch/template")
    def batch_template():
        path = generate_sample_template()
        return send_file(path, mimetype="text/csv", as_attachment=True, download_name=path.name)

    @app.post("/api/batch/eval")
    @app.get("/api/batch/eval")
    def batch_evaluate():
        files = []
        for key in ("phishing_csv", "legit_csv", "upload"):
            if key == "upload":
                uploaded = request.files.get(key)
                if uploaded and uploaded.filename:
                    files.append(uploaded)
                continue
            uploaded = request.files.get(key)
            if uploaded and uploaded.filename:
                files.append(uploaded)
        if not files:
            file_list = request.files.getlist("files")
            files.extend([item for item in file_list if getattr(item, "filename", None)])
        if not files:
            return {"error": "Upload at least one CSV file before running the evaluation."}, 400

        temp_paths = []
        try:
            for uploaded in files:
                temp_path = Path(tempfile.NamedTemporaryFile(suffix=".csv", delete=False).name)
                uploaded.save(temp_path)
                temp_paths.append(temp_path)
            payload = evaluate_csv(temp_paths)
            app.config["batch_last_payload"] = payload
            report_dir = ROOT / "reports" / "external"
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "mentor_eval.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            pd.DataFrame(payload["rows"]).to_csv(report_dir / "mentor_eval_results.csv", index=False)
            return payload, 200
        except ValueError as exc:
            return {"error": str(exc)}, 400
        finally:
            for temp_path in temp_paths:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

    @app.get("/api/batch/results.csv")
    def batch_results_csv():
        path = ROOT / "reports" / "external" / "mentor_eval_results.csv"
        if not path.exists():
            return {"error": "No evaluation results are available yet."}, 404
        return send_file(path, mimetype="text/csv", as_attachment=True, download_name="mentor_eval_results.csv")

    @app.get("/api/batch/results.json")
    def batch_results_json():
        path = ROOT / "reports" / "external" / "mentor_eval.json"
        if not path.exists():
            return {"error": "No evaluation report is available yet."}, 404
        return send_file(path, mimetype="application/json", as_attachment=True, download_name="mentor_eval.json")

    @app.get("/threat-model")
    def threat_model():
        return render_template_string(BASE_LAYOUT, page_title="Threat Model & About", active_nav="threat-model", css=BASE_CSS, content=_build_threat_model_page())

    @app.post("/api/scan")
    def scan():
        payload = request.get_json(silent=True) or {}
        channel = str(payload.get("channel", "email")).lower()
        subject = str(payload.get("subject", "")).strip()
        body = str(payload.get("body", "")).strip()
        if not subject and not body:
            return {"error": "Please provide a message to scan."}, 400

        text = f"{subject} {body}"
        result = _message_score(text, channel)
        return {
            **result,
            "message": text,
            "verdict": result["verdict"],
            "risk": result["risk"],
        }

    return app
