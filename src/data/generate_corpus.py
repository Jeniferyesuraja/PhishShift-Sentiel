from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
DOCS_DIR = ROOT / "docs"
RAW_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
random.seed(SEED)

CAMPAIGNS = [
    {"group": "fake_invoice", "label": "phishing", "channels": ["email", "sms"], "domain_types": ["lookalike", "unknown", "freemail"]},
    {"group": "parcel_fee", "label": "phishing", "channels": ["email", "sms"], "domain_types": ["shortener", "lookalike", "unknown"]},
    {"group": "mfa_fatigue", "label": "phishing", "channels": ["email", "sms"], "domain_types": ["shortener", "unknown", "lookalike"]},
    {"group": "ceo_gift_card", "label": "phishing", "channels": ["email"], "domain_types": ["lookalike", "freemail", "unknown"]},
    {"group": "payroll_update", "label": "phishing", "channels": ["email", "sms"], "domain_types": ["shortener", "unknown", "lookalike"]},
    {"group": "storage_full", "label": "phishing", "channels": ["email", "sms"], "domain_types": ["lookalike", "shortener", "unknown"]},
    {"group": "shortened_prize", "label": "phishing", "channels": ["sms", "email"], "domain_types": ["shortener", "unknown", "freemail"]},
    {"group": "hr_policy", "label": "phishing", "channels": ["email"], "domain_types": ["lookalike", "shortener", "unknown"]},
    {"group": "vpn_expiry", "label": "phishing", "channels": ["email", "sms"], "domain_types": ["lookalike", "shortener", "unknown"]},
    {"group": "qr_sms_smish", "label": "phishing", "channels": ["sms"], "domain_types": ["shortener", "unknown", "lookalike"]},
    {"group": "password_reset", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", "corporate", "unknown"]},
    {"group": "payroll_slip", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", "corporate", "unknown"]},
    {"group": "it_maintenance", "label": "legitimate", "channels": ["email"], "domain_types": ["corporate", "corporate", "unknown"]},
    {"group": "security_alert", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", "corporate", "unknown"]},
    {"group": "travel_approval", "label": "legitimate", "channels": ["email"], "domain_types": ["corporate", "corporate", "unknown"]},
    {"group": "benefits_enrollment", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", "unknown", "freemail"]},
    {"group": "team_meeting", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", "corporate", "unknown"]},
    {"group": "vendor_invoice", "label": "legitimate", "channels": ["email"], "domain_types": ["corporate", "unknown", "freemail"]},
]

PHISHING_URLS = [
    "hxxp://secure[.]portal[.]review/login",
    "hxxps://update[.]account[.]verify/confirm",
    "hxxp://urgent[.]doc[.]delivery/secure",
    "hxxp://bitly[.]link/claim-reward",
    "hxxp://verify[.]workplace[.]alert/submit",
    "hxxp://vault[.]payment[.]access/confirm",
    "hxxps://short[.]link[.]co/offer",
    "hxxp://staff[.]payroll[.]action/response",
    "hxxp://mfa[.]service[.]fix/alert",
    "hxxp://secure[.]access[.]host/restore",
]

LEGIT_URLS = [
    "hxxps://status[.]company[.]com/security-reset",
    "hxxps://payroll[.]company[.]com/slip",
    "hxxp://help[.]company[.]com/maintenance",
    "hxxps://alerts[.]company[.]com/verify-action",
    "hxxp://portal[.]company[.]com/travel-approval",
    "hxxps://benefits[.]company[.]com/enrollment",
    "hxxp://calendar[.]company[.]com/meeting",
    "hxxps://vendor[.]company[.]com/invoice",
]


def make_url_features(url: str) -> dict:
    host = url.replace("hxxp://", "").replace("hxxps://", "")
    domain = host.split("/")[0]
    path = "/".join(host.split("/")[1:])
    path_depth = max(len([part for part in path.split("/") if part]), 0)
    return {
        "url_count": 1,
        "has_shortener": any(token in domain.lower() for token in ["bitly", "tinyurl", "goo.gl", "link", "short", "rebrand"]),
        "has_ip_host": any(ch.isdigit() for ch in domain),
        "num_dots": domain.count("[.]"),
        "has_at_symbol": "@" in url,
        "path_depth": path_depth,
        "tld_class": "shortener" if "short" in domain.lower() or "bitly" in domain.lower() else "unknown",
        "lookalike_score": 0.8 if any(token in domain.lower() for token in ["verify", "secure", "portal", "access"]) else 0.2,
        "defanged": True,
    }


def defang_url(url: str) -> str:
    if not url:
        return url
    cleaned = url.strip()
    cleaned = cleaned.replace("https://", "hxxps://").replace("http://", "hxxp://")
    cleaned = cleaned.replace(".", "[.]")
    return cleaned


def generate_rows() -> list[dict]:
    rows: list[dict] = []
    campaign_counter = Counter()
    start_date = datetime(2024, 1, 10)

    for campaign in CAMPAIGNS:
        group = campaign["group"]
        label = campaign["label"]
        for idx in range(28):
            campaign_counter[group] += 1
            channel = random.choice(campaign["channels"])
            if idx % 5 == 0:
                channel = channel.upper()
            sender_domain_type = random.choice(campaign["domain_types"])
            if label == "phishing":
                base_url = random.choice(PHISHING_URLS)
                subject = random.choice([
                    "Urgent action required",
                    "Account verification needed",
                    "Final invoice notice",
                    "Security alert - update now",
                    "Action required today",
                    "Payroll correction needed",
                ])
                body_variants = [
                    "Your account has been flagged. Review the secure portal and confirm your details before noon.",
                    "We noticed unusual access to your mailbox. Please verify this request now to avoid lockout.",
                    "This is a final reminder: complete the requested update to keep your account active.",
                    "A payment request requires your approval today, and delay may cause service interruption.",
                ]
                body = body_variants[idx % len(body_variants)]
                if idx % 4 == 0:
                    body = body.replace("account", "profile")
                    body = body.replace("secure portal", "secure portal access")
            else:
                base_url = random.choice(LEGIT_URLS)
                subject = random.choice([
                    "Password reset confirmation",
                    "Payroll slip available",
                    "Scheduled IT maintenance",
                    "Security alert from corporate systems",
                    "Travel approval approved",
                    "Benefits enrollment reminder",
                ])
                body_variants = [
                    "Your password reset was completed successfully. If you did not request this, contact the service desk.",
                    "Payroll slip is now available in the company portal, no action required.",
                    "We are performing scheduled maintenance between 10:00 PM and 11:00 PM. There is no impact to your work.",
                    "A new security alert has been generated from corporate systems and is available in the portal.",
                ]
                body = body_variants[idx % len(body_variants)]
                if idx % 6 == 0:
                    body = body + " This is a routine reminder from the helpdesk."

            if idx % 9 == 0:
                subject = ""
            if idx % 11 == 0:
                body = body + " Please ignore if this is not relevant."
            if idx % 13 == 0:
                body = body.replace(" ", "  ")

            collected_date = start_date + timedelta(days=(idx * 4 + len(group) * 3) % 120)
            message_id = f"{group}_{idx + 1:03d}"
            row = {
                "message_id": message_id,
                "channel": channel,
                "subject_or_title": subject,
                "body_text": body,
                "sanitized_url_features": json.dumps(make_url_features(base_url), sort_keys=True),
                "sender_domain_type": sender_domain_type,
                "label": label,
                "campaign_group": group,
                "collected_date": collected_date.strftime("%Y-%m-%d"),
            }
            if idx % 7 == 0:
                row["channel"] = random.choice(["email", "sms", "EMAIL", "Sms"])
            rows.append(row)

    return rows


def write_manifest(rows: list[dict]) -> None:
    counts = defaultdict(lambda: {"email": 0, "sms": 0})
    for row in rows:
        counts[row["campaign_group"]][row["channel"].lower()] += 1

    entries = []
    for campaign in CAMPAIGNS:
        group = campaign["group"]
        label = campaign["label"]
        channel_counts = counts[group]
        entries.append(
            {
                "campaign_group": group,
                "label": label,
                "count": sum(channel_counts.values()),
                "channel_email": channel_counts.get("email", 0),
                "channel_sms": channel_counts.get("sms", 0),
                "source": "locally authored",
                "license": "CC0",
                "seed": SEED,
                "generated_date": datetime.now().strftime("%Y-%m-%d"),
            }
        )

    manifest = pd.DataFrame(entries)
    manifest.to_csv(ROOT / "data" / "SOURCE_MANIFEST.csv", index=False)

    provenance = ROOT / "docs" / "corpus_provenance.md"
    lines = [
        "# Corpus provenance",
        "",
        "- Source: locally authored synthetic campaign data",
        "- License: CC0",
        f"- Generation seed: {SEED}",
        f"- Date: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Counts by campaign",
        "",
    ]
    for row in entries:
        lines.append(
            f"- {row['campaign_group']} ({row['label']}): total={row['count']}, email={row['channel_email']}, sms={row['channel_sms']}"
        )
    provenance.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = generate_rows()
    data = pd.DataFrame(rows)
    output_path = RAW_DIR / "phishshift_raw.csv"
    data.to_csv(output_path, index=False)
    write_manifest(rows)
    print(f"Generated {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
