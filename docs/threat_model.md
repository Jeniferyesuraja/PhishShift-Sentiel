# Threat Model & About

> Decision support only - not a guarantee of safety.

## Threat model overview

The system is designed for educational and defensive triage, not for autonomous blocking or live URL analysis. It captures common phishing patterns in a local synthetic corpus and explains the signals it used before the analyst makes a decision.

| Threat | Attacker goal | Example cue | Mitigation in this system | Residual risk |
| --- | --- | --- | --- | --- |
| Urgency pressure | Drive a fast, low-thought decision | “Verify your account now before access is suspended.” | Flags urgency verbs and time pressure, then explains the cue in the rationale view. | Real operational messages can also be urgent and require human review. |
| Shortened or defanged links | Hide the destination or prevent inspection | hxxp://example[.]com/reset or a short-link token | Defangs URLs and tracks link-lure patterns without opening the target | Obfuscated or novel link text may still confuse the model. |
| Lookalike sender domains | Impersonate a trusted brand or helpdesk | security@micr0soft-help.com | Adds sender-domain mismatch and brand impersonation cues to the score | Header authentication (SPF/DKIM) is not evaluated in this lab. |
| Credential harvesting | Steal account access or MFA tokens | “Enter your password and one-time code” | Raises a strong phishing score for credential-request phrasing | Some legitimate workflows still trigger confirmation requests in context. |
| Unfamiliar wording / distribution shift | Exploit language the model has not seen before | New campaign phrasing or multilingual phrasing | Relies on explainable rules and grouped-holdout checks, not a single model | Unseen wording can still reduce confidence or trigger abstain. |
| Adversarial punctuation and synonym changes | Bypass a simple lexical model | “P@ssw0rd”, “s3cure”, extra punctuation | Normalizes and scores the salient text, then surfaces the cue rationale | Text-only perturbations can still evade narrow linguistic heuristics. |
| Legit-urgent messages causing false positives | Confuse the model with real operational urgency | “Payroll approval is needed before 5 PM” | Explains the context and uses abstain logic for uncertain cases | High-urgency legitimate traffic may still be escalated for review. |

## Assets and trust boundaries

### Protected assets

- Analyst decision quality for email and SMS triage.
- Local synthetic corpus and model explanation artifacts.
- Safety notices that prevent over-trusting model output.

### Boundaries and controls

- No live URL fetching or external content inspection.
- No attachment handling or credential collection.
- No real credentials, PII, or production inbox content is used.
- URLs are stored in defanged form such as hxxp://example[.]com/...

### Data flow

```text
User message
  -> local sanitization (defang URLs, normalize text)
  -> rule and TF-IDF models
  -> analyst review with explanations and warning banner
```

## Known limitations

- Synthetic data only: training and evaluation are local, safe, and educational.
- Small corpus: performance is tuned on a limited set of synthetic campaigns.
- English only: multilingual or region-specific phrasing is not represented.
- No SPF/DKIM/DMARC header checks: sender authentication is out of scope.
- Probabilities are not calibrated guarantees and are not equivalent to a production security control.
- The abstain threshold is tuned on a limited number of campaigns and should be revalidated before use in a new environment.

## Dataset license and provenance

- Source: locally authored synthetic campaign data.
- License: CC0.
- Generation seed: 42.
- Date: 2026-10-23.
- Dataset size: 504 rows across 18 campaigns.

### Campaign row counts

| Campaign | Rows |
| --- | ---: |
| fake_invoice | 28 |
| parcel_fee | 28 |
| mfa_fatigue | 28 |
| ceo_gift_card | 28 |
| payroll_update | 28 |
| storage_full | 28 |
| shortened_prize | 28 |
| hr_policy | 28 |
| vpn_expiry | 28 |
| qr_sms_smish | 28 |
| password_reset | 28 |
| payroll_slip | 28 |
| it_maintenance | 28 |
| security_alert | 28 |
| travel_approval | 28 |
| benefits_enrollment | 28 |
| team_meeting | 28 |
| vendor_invoice | 28 |

## Model card summary

The model summary is derived from the tracked artifacts in the repository:

- Model version: phishshift-sentinel-v1.0
- Train date: 2026-10-23
- Dataset size: 504 rows across 18 synthetic campaigns
- Split strategy: grouped holdout by campaign_group
- Primary metric: grouped-holdout F1 for TF-IDF Logistic Regression = 0.6667

## AI usage disclosure

### AI-assisted components

- Drafting the threat-model narrative and risk taxonomy.
- Structuring the page layout and supporting documentation.
- Suggesting phrasing for the residual-risk and limitations sections.

### What was verified manually

- [ ] code reproduced locally
- [ ] results re-run after edits
- [ ] citations and provenance checked against project artifacts
- [ ] safety warning kept consistent across the app and docs

## Safety note

This project is intended for educational and defensive use in phishing-risk triage. It is not a production security control and should be treated as an analyst aid rather than an autonomous decision engine.
