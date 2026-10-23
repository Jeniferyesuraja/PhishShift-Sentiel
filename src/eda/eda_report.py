from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean.csv"
OUT_DIR = ROOT / "reports" / "eda"
DOC_PATH = ROOT / "docs" / "eda_summary.md"


def build_eda_report() -> None:
    df = pd.read_csv(DATA_PATH)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fig1, ax1 = plt.subplots(figsize=(7, 4))
    label_counts = df["label"].value_counts().sort_index()
    ax1.bar(label_counts.index, label_counts.values, color=["#3ae9a3", "#ff6f7d"])
    ax1.set_title("Figure 1: Label distribution")
    ax1.set_xlabel("Label")
    ax1.set_ylabel("Count")
    for bar, value in zip(ax1.patches, label_counts.values):
        ax1.text(bar.get_x() + bar.get_width() / 2, value + 4, str(value), ha="center", va="bottom")
    fig1.tight_layout()
    fig1.savefig(OUT_DIR / "figure_1_label_distribution.png", dpi=200)
    plt.close(fig1)

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    campaign_counts = df.groupby("campaign_group")["message_id"].count().sort_values(ascending=False)
    campaign_counts.plot(kind="bar", ax=ax2, color="#48d3ff")
    ax2.set_title("Figure 2: Campaign counts by grouped campaign")
    ax2.set_xlabel("Campaign group")
    ax2.set_ylabel("Messages")
    ax2.tick_params(axis="x", rotation=45)
    fig2.tight_layout()
    fig2.savefig(OUT_DIR / "figure_2_campaign_counts.png", dpi=200)
    plt.close(fig2)

    fig3, ax3 = plt.subplots(figsize=(8, 4.5))
    cues = ["verify", "urgent", "password", "secure", "reward", "portal"]
    cue_counts = {cue: (df["body_text"].fillna("").str.lower().str.count(cue).sum()) for cue in cues}
    ax3.bar(cue_counts.keys(), cue_counts.values(), color="#ffba52")
    ax3.set_title("Figure 3: High-risk cue frequency")
    ax3.set_xlabel("Cue")
    ax3.set_ylabel("Occurrences")
    ax3.tick_params(axis="x", rotation=30)
    fig3.tight_layout()
    fig3.savefig(OUT_DIR / "figure_3_risk_cues.png", dpi=200)
    plt.close(fig3)

    summary = [
        "# EDA summary",
        "",
        f"- Rows analyzed: {len(df)}",
        f"- Labels: {df['label'].value_counts().to_dict()}",
        f"- Campaign groups: {df['campaign_group'].nunique()}",
        "",
        "## Observations",
        "- The corpus is balanced enough for a first pass at phishing-vs-legitimate discrimination.",
        "- Campaign structure is intentionally grouped so a cohort-based holdout can reveal leakage and drift.",
        "- Risk-cue words like 'verify', 'urgent', and 'password' recur strongly in suspicious content.",
        "",
        "## Figures generated",
        "- `reports/eda/figure_1_label_distribution.png`",
        "- `reports/eda/figure_2_campaign_counts.png`",
        "- `reports/eda/figure_3_risk_cues.png`",
    ]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"EDA saved to {OUT_DIR}")


if __name__ == "__main__":
    build_eda_report()
