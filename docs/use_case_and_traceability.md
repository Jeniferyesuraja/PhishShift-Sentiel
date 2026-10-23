# Use case and traceability

## Use case
The system supports a helpdesk analyst reviewing inbound email and SMS messages. It summarizes risk, notes suspicious cues, and recommends escalation without opening links or collecting real secrets.

## Target definition
The product detects suspicious messaging patterns that resemble scam content but does not guarantee maliciousness. It is intended for training and triage workflows, not autonomous decision-making.

## Decision for the user
The analyst reads the verdict and explanation, then decides whether to escalate or ignore. The system is explicitly advisory.

## Exclusions
- No live URL resolution or fetches.
- No attachments or external content fetching.
- No real credentials, mailboxes, or personal data.
- No live internet tasks are allowed.

## Traceability matrix
| Requirement | Module | Test evidence |
| --- | --- | --- |
| FR-01 Deduplication | src/data/dedup.py | tests/test_split.py |
| FR-02 Model comparison | src/models/train.py | reports/results_table.md |
| FR-03 Campaign holdout | src/data/split.py | tests/test_split.py |
| FR-04 Abstention | src/models/abstain.py | reports/acceptance/ |
| FR-05 Robustness | src/robustness/perturb.py | reports/robustness_drift.csv |
| NFR-01 No live fetching | src/data/sanitize.py | tests/test_sanitize.py |
| NFR-02 Synthetic only | docs/corpus_provenance.md | data/SOURCE_MANIFEST.csv |
| NFR-03 UI banner | app/templates | app smoke tests |
| AT-01 to AT-03 | tests/acceptance | reports/acceptance/ |
