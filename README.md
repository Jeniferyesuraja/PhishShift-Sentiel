# PhishShift Message Risk Scanner

PhishShift is a synthetic, educational phishing-risk detector for helpdesk triage. It uses campaign-structured data, rule cues, text models, and robustness checks to explain why a message looks risky without opening links or collecting secrets.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Data generation

```bash
python -m src.data.generate_corpus
python -m src.data.clean
```

## Tests

```bash
python -m pytest -q
```

## Notes

- All URLs are defanged and never clickable.
- Decision support only - not a guarantee of safety.
- AI usage disclosure: this project was built with local authoring, synthetic data generation, and code assistance during implementation.
