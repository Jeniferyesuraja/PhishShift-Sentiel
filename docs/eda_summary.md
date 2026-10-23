# EDA summary

- Rows analyzed: 504
- Labels: {'phishing': 280, 'legitimate': 224}
- Campaign groups: 18

## Observations
- The corpus is balanced enough for a first pass at phishing-vs-legitimate discrimination.
- Campaign structure is intentionally grouped so a cohort-based holdout can reveal leakage and drift.
- Risk-cue words like 'verify', 'urgent', and 'password' recur strongly in suspicious content.

## Figures generated
- `reports/eda/figure_1_label_distribution.png`
- `reports/eda/figure_2_campaign_counts.png`
- `reports/eda/figure_3_risk_cues.png`
