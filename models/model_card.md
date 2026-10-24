# Model card

- Model version: phishshift-sentinel-v1.0
- Train date: 2026-10-23
- Dataset size: 504 rows across 18 synthetic campaigns
- Split strategy: grouped holdout by campaign_group; holdout campaigns were qr_sms_smish, vendor_invoice, and it_maintenance
- Primary metric: grouped-holdout F1 for TF-IDF Logistic Regression = 0.6667
- Intended use: helpdesk triage for synthetic phishing-risk review in a controlled evaluation setting
- Data: locally authored synthetic corpus with defanged URLs and no real credentials or PII
- Limits: not a guarantee of safety; not for live URL analysis; not for production authentication or DMARC checks
- Ethics: educational and defensive use only
- Safety warning: Decision support only - not a guarantee of safety.
