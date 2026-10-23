from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.data.sanitize import sanitize_record

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "data" / "raw" / "phishshift_raw.csv"
OUT_PATH = ROOT / "data" / "processed" / "clean.csv"
LOG_PATH = ROOT / "reports" / "cleaning_log.md"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    df = pd.read_csv(RAW_PATH)
    cleaned_rows = []
    for row in df.to_dict(orient="records"):
        cleaned_rows.append(sanitize_record(row))
    clean_df = pd.DataFrame(cleaned_rows)
    clean_df.to_csv(OUT_PATH, index=False)

    raw_hash = compute_sha256(RAW_PATH)
    log_lines = [
        "# Cleaning log",
        "",
        f"- Input raw file: {RAW_PATH}",
        f"- Raw checksum: {raw_hash}",
        f"- Rows processed: {len(clean_df)}",
        "",
        "## Fixes applied",
        "- Lowercased channel labels and normalized labels.",
        "- Defanged URL strings and extracted sanitized URL features.",
        "- Redacted email addresses, phone numbers, credentials, and attachment references.",
        "- Preserved raw data and wrote cleaned data to the processed directory.",
        "",
        "## Summary",
        f"- Unique campaigns: {clean_df['campaign_group'].nunique()}",
        f"- Legitimate rows: {(clean_df['label'] == 'legitimate').sum()}",
        f"- Phishing rows: {(clean_df['label'] == 'phishing').sum()}",
    ]
    LOG_PATH.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"Cleaned dataset written to {OUT_PATH}")


if __name__ == "__main__":
    main()
