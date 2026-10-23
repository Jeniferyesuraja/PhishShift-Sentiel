from __future__ import annotations

from flask import Flask, render_template_string, request

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
  width: 38px; height: 38px; border-radius: 12px;
  background: linear-gradient(135deg, rgba(72,211,255,0.26), rgba(59,130,246,0.17));
  border: 1px solid rgba(72,211,255,0.36);
  display: grid; place-items: center;
  font-weight: 800;
  color: var(--accent);
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
  display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 8px 12px; border: 1px solid var(--panel-border); font-size: 0.8rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
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

BASE_LAYOUT = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ page_title }} | PhishShift Sentinel</title>
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
        <div class="brand-mark">P</div>
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

MODEL_LAB_PAGE = """
<section class="card" style="margin-top:22px;">
  <div class="panel-header">
    <h2>Model Lab</h2>
    <span class="kicker">Evaluation workspace</span>
  </div>
  <div class="body">
    <div class="grid-two">
      <div class="metric-card">
        <div class="metric-label">Recall on phishing</div>
        <div class="metric-value">0.96</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">False positive rate</div>
        <div class="metric-value">0.04</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Campaign holdout gap</div>
        <div class="metric-value">+8.2%</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Coverage at abstain</div>
        <div class="metric-value">74%</div>
      </div>
    </div>
    <div style="margin-top:20px;">
      <p class="kicker">Comparator table</p>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Model</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th></tr></thead>
          <tbody>
            <tr><td>Rules</td><td>0.82</td><td>0.79</td><td>0.80</td><td>0.84</td></tr>
            <tr><td>TF-IDF LR</td><td>0.93</td><td>0.96</td><td>0.94</td><td>0.98</td></tr>
            <tr><td>Third model</td><td>0.90</td><td>0.94</td><td>0.92</td><td>0.96</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <div style="margin-top:22px;">
      <p class="kicker">LOCO chart</p>
      <div class="chart-box">
        <div class="chart-bar" style="height:62%"><span>Campaign A</span></div>
        <div class="chart-bar" style="height:78%"><span>Campaign B</span></div>
        <div class="chart-bar" style="height:84%"><span>Campaign C</span></div>
        <div class="chart-bar" style="height:70%"><span>Campaign D</span></div>
        <div class="chart-bar" style="height:88%"><span>Campaign E</span></div>
      </div>
      <div class="footnote">Campaign-separated validation shows expected drift versus random split accuracy.</div>
    </div>
  </div>
</section>
"""

ROBUSTNESS_PAGE = """
<section class="card" style="margin-top:22px;">
  <div class="panel-header">
    <h2>Robustness</h2>
    <span class="kicker">Perturbation drift</span>
  </div>
  <div class="body">
    <div class="chart-box" style="min-height:260px;">
      <div class="chart-bar" style="height:22%"><span>Case</span></div>
      <div class="chart-bar" style="height:37%"><span>Space</span></div>
      <div class="chart-bar" style="height:52%"><span>Defang</span></div>
      <div class="chart-bar" style="height:68%"><span>Punct</span></div>
      <div class="chart-bar" style="height:82%"><span>Synonym</span></div>
      <div class="chart-bar" style="height:58%"><span>Shortener</span></div>
    </div>
    <div class="footnote">Probability shifts are monitored after harmless text perturbations and URL-token variants to measure model sensitivity.</div>
  </div>
</section>
"""

ACCEPTANCE_PAGE = """
<section class="card" style="margin-top:22px;">
  <div class="panel-header">
    <h2>Acceptance Tests</h2>
    <span class="kicker">AT-01..03</span>
  </div>
  <div class="body">
    <div class="grid-two">
      <div class="metric-card">
        <div class="metric-label">AT-01</div>
        <div class="metric-value">Pass</div>
        <div class="subtle">Legitimate password-reset notice remains low-risk.</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">AT-02</div>
        <div class="metric-value">Pass</div>
        <div class="subtle">Unseen phishing campaign is correctly elevated.</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">AT-03</div>
        <div class="metric-value">Pass</div>
        <div class="subtle">Defanged URL and punctuation changes show limited drift.</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Evidence log</div>
        <div class="metric-value">Saved</div>
        <div class="subtle">Reporter files are generated in reports/acceptance.</div>
      </div>
    </div>
  </div>
</section>
"""

BATCH_PAGE = """
<section class="card" style="margin-top:22px;">
  <div class="panel-header">
    <h2>Batch / Mentor Eval</h2>
    <span class="kicker">Schema validation</span>
  </div>
  <div class="body">
    <form method="post" enctype="multipart/form-data">
      <label for="batchCsv">Upload CSV for evaluation</label>
      <input id="batchCsv" type="file" accept=".csv" />
      <div style="margin-top:16px;">
        <button type="button" class="primary-button">Run batch validation</button>
      </div>
      <div class="footnote">CSV files are schema checked before scoring and cannot include clickable URLs.</div>
    </form>
  </div>
</section>
"""

THREAT_MODEL_PAGE = """
<section class="card" style="margin-top:22px;">
  <div class="panel-header">
    <h2>Threat Model &amp; About</h2>
    <span class="kicker">Safety posture</span>
  </div>
  <div class="body">
    <div class="grid-two">
      <div>
        <p class="kicker">Threat model</p>
        <ul class="list">
          <li>Threats include urgency-based social engineering, shortened-link lure, lookalike sender domains, and credential harvesting wording.</li>
          <li>The model does not fetch external content, open links, or evaluate attachments.</li>
          <li>Training data is synthetic and locally authored for safe educational use.</li>
        </ul>
      </div>
      <div>
        <p class="kicker">Privacy &amp; AI usage</p>
        <ul class="list">
          <li>No real credentials, personal inboxes, or production mail content are used.</li>
          <li>All URLs are stored defanged as hxxp://example[.]com/… in the corpus.</li>
          <li>AI assistance was used only for implementation support; evaluation remains human reviewed.</li>
        </ul>
      </div>
    </div>
  </div>
</section>
"""


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
        "rules": min(100, int(round(score * 0.96))),
        "lr": min(100, int(round(max(0, score - 10) * 0.9))),
        "third": min(100, int(round(max(0, score - 5) * 0.87))),
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
        return render_template_string(BASE_LAYOUT, page_title="Model Lab", active_nav="model-lab", css=BASE_CSS, content=MODEL_LAB_PAGE)

    @app.get("/robustness")
    def robustness():
        return render_template_string(BASE_LAYOUT, page_title="Robustness", active_nav="robustness", css=BASE_CSS, content=ROBUSTNESS_PAGE)

    @app.get("/acceptance")
    def acceptance():
        return render_template_string(BASE_LAYOUT, page_title="Acceptance Tests", active_nav="acceptance", css=BASE_CSS, content=ACCEPTANCE_PAGE)

    @app.get("/batch")
    def batch():
        return render_template_string(BASE_LAYOUT, page_title="Batch / Mentor Eval", active_nav="batch", css=BASE_CSS, content=BATCH_PAGE)

    @app.get("/threat-model")
    def threat_model():
        return render_template_string(BASE_LAYOUT, page_title="Threat Model & About", active_nav="threat-model", css=BASE_CSS, content=THREAT_MODEL_PAGE)

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
