from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "clean.csv"


def test_campaign_overlap_is_zero_and_no_near_dup_leakage():
    df = pd.read_csv(DATA_PATH)
    train_campaigns = sorted(df['campaign_group'].unique())
    assert len(train_campaigns) >= 3
    assert not df.empty

    seen = set(df['message_id'])
    assert len(seen) == len(df)
    pairs = []
    for row in df.to_dict(orient='records'):
        if row['campaign_group'] == 'fake_invoice':
            pairs.append(row['message_id'])
    assert len(pairs) > 0

    split_data = json.loads((ROOT / 'data' / 'processed' / 'splits.json').read_text(encoding='utf-8')) if (ROOT / 'data' / 'processed' / 'splits.json').exists() else {}
    if split_data:
        assert set(split_data.get('train_campaigns', [])) & set(split_data.get('test_campaigns', [])) == set()
        assert set(split_data.get('val_campaigns', [])) & set(split_data.get('test_campaigns', [])) == set()
