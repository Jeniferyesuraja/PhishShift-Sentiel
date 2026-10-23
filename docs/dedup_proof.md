# Deduplication proof

- Rows before deduplication: 504
- Rows after deduplication: 423
- Removed rows: 81
- Threshold used: cosine similarity >= 0.90 on TF-IDF text representation.
- This step runs before splitting to avoid test leakage from near-duplicates.

## Audit summary
- Near-duplicate pairs identified: 1882
- The proof is stored in `reports/dedup_audit.csv` and is reviewed before any split is accepted.

## Assertion
The pipeline asserts that near-duplicate examples are either kept once or reviewed before train/test separation.
