# PhishShift Sentinel

PhishShift Sentinel is a synthetic, educational phishing-risk scanner for helpdesk triage. It scores incoming email/SMS content, explains the signals that triggered the score, and avoids opening any live links.

Spot the shift. Stop the phish.

## Features

- Explainable rules model
- TF-IDF Logistic Regression baseline
- Third model comparison
- Campaign-grouped split validation
- Abstain logic and robustness checks
- Premium dark SOC-style dashboard
- Synthetic-only, defanged URL handling

## Quick start

```powershell
cd "c:\Users\jeni pc\OneDrive\Desktop\phishShift"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
python -c "from app import create_app; app = create_app(); app.run(host='127.0.0.1', port=5000, debug=True)"
```

Open:

```text
http://127.0.0.1:5000/
```

## Data and model workflow

```powershell
python -m src.data.generate_corpus
python -m src.data.clean
python -m src.data.split
python -m src.models.train
```

## Safety notes

- No live URL fetching or link opening
- Only synthetic data is used
- URLs are defanged as hxxp://example[.]com/...
- Decision support only - not a guarantee of safety.

## Project status

This project is built for educational and defensive use in phishing-risk triage workflows. It is not a production security control and should be treated as an analyst aid rather than an autonomous decision engine. The project name is PhishShift Sentinel, with the tagline: Spot the shift. Stop the phish.
