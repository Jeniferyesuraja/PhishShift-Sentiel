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
    {"group": "password_reset", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", "freemail", "unknown"]},
    {"group": "payroll_slip", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", "freemail", "unknown"]},
    {"group": "it_maintenance", "label": "legitimate", "channels": ["email"], "domain_types": ["corporate", "unknown", "freemail"]},
    {"group": "security_alert", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", " unknown", "freemail"]},
    {"group": "travel_approval", "label": "legitimate", "channels": ["email"], "domain_types": ["corporate", "unknown", "freemail"]},
    {"group": "benefits_enrollment", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", "unknown", "freemail"]},
    {"group": "team_meeting", "label": "legitimate", "channels": ["email", "sms"], "domain_types": ["corporate", "unknown", "freemail"]},
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

PHISHING_TEMPLATES = [
    "We are checking recent account activity and the portal is asking for a quick confirmation so the review can close without disruption.",
    "A recent account mismatch was flagged during the regular review cycle, and the access status still needs a final check before the update is cleared.",
    "Your approval request is still in the account queue. Please review the latest portal note and confirm the current status before the deadline.",
    "This notice is part of the account verification workflow and the portal suggests a final check before the reminder expires.",
    "The access review detected a change in your latest session data. Please confirm the record in the portal to keep the account active.",
    "The latest security review highlighted an outstanding access note. Please check the account details and complete the review before the end of the day.",
]

LEGIT_TEMPLATES = [
    "We are checking recent account activity as part of the routine review. No action is required unless a change was expected to your access settings.",
    "A recent account mismatch was reviewed during the standard operation and the access status remains unchanged without any follow-up needed.",
    "Your approval request was processed during the normal account queue and no additional confirmation is required at this time.",
    "This notice is part of the standard verification workflow and the portal note is for reference only. No urgent action is required.",
    "The access review detected no unusual changes in your latest session data and confirms the account remains active with no additional steps.",
    "The latest security review highlights no outstanding issues. Please keep the portal note for reference and contact support only if a change was expected.",
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
    cleaned = url.strip().replace("https://", "hxxps://").replace("http://", "hxxp://")
    return cleaned.replace(".", "[.]")


def generate_rows() -> list[dict]:
    rows: list[dict] = []
    start_date = datetime(2024, 1, 10)
    for campaign_index, campaign in enumerate(CAMPAIGNS):
        group = campaign["group"]
        label = campaign["label"]
        for idx in range(28):
            channel = random.choice(campaign["channels"]).lower()
            if idx % 5 == 0:
                channel = "sms" if channel == "email" else "email"
            sender_domain_type = random.choice(campaign["domain_types"])
            common_subjects = [
                "Account update",
                "Security review",
                "Access notice",
                "Portal status",
                "Tax or billing follow-up",
                "Service reminder",
            ]
            if label == "phishing":
                sender_domain_type = random.choice(["lookalike", "unknown", "freemail", "corporate"])
                subject = random.choice(common_subjects)
                body = random.choice(PHISHING_TEMPLATES)
                if idx % 4 == 0:
                    body = body + " The portal check is time-sensitive and should be completed before the reminder closes."
                if idx % 6 == 0:
                    body = body + " Please review the current status and confirm the latest access note."
                if idx % 9 == 0:
                    body = body + " This notice is informational, but the account team recommends action before the review closes."
                base_url = random.choice(PHISHING_URLS)
            else:
                sender_domain_type = random.choice(["corporate", "unknown", "freemail", "lookalike"])
                subject = random.choice(common_subjects)
                body = random.choice(LEGIT_TEMPLATES)
                if group in {"password_reset", "payroll_slip"} and idx % 3 == 0:
                    body = body + " This communication is informational and no urgent action is required."
                if idx % 7 == 0:
                    body = body + " If you did not make this request, contact the service desk to review the status, but no action is needed unless you expect a change."
                if idx % 11 == 0:
                    body = body + " The current account status remains active and the review is complete."
                base_url = random.choice(LEGIT_URLS)

            if idx % 9 == 0:
                subject = ""
            if idx % 11 == 0:
                body = body + " Please ignore if this is not relevant."
            if idx % 13 == 0:
                body = body.replace(" ", "  ")

            row = {
                "message_id": f"{group}_{idx + 1:03d}",
                "channel": channel,
                "subject_or_title": subject,
                "body_text": body,
                "sanitized_url_features": json.dumps(make_url_features(base_url), sort_keys=True),
                "sender_domain_type": sender_domain_type,
                "label": label,
                "campaign_group": group,
                "collected_date": (start_date + timedelta(days=(campaign_index * 3 + idx * 5) % 150)).strftime("%Y-%m-%d"),
            }
            rows.append(row)

    return rows


def write_manifest(rows: list[dict]) -> None:
    counts = defaultdict(lambda: {"email": 0, "sms": 0})
    for row in rows:
        counts[row["campaign_group"]][row["channel"].lower()] += 1
    entries = []
    for campaign in CAMPAIGNS:
        group = campaign["group"]
        df = counts[group]
        entries.append(
            {
                "campaign_group": group,
                "label": campaign["label"],
                "count": df.get("email", 0) + df.get("sms", 0),
                "channel_email": df.get("email", 0),
                "channel_sms": df.get("sms", 0),
                "source": "locally authored",
                "license": "CC0",
                "seed": SEED,
                "generated_date": datetime.now().strftime("%Y-%m-%d"),
            }
        )
    pd.DataFrame(entries).to_csv(ROOT / "data" / "SOURCE_MANIFEST.csv", index=False)


def main() -> None:
    rows = generate_rows()
    data = pd.DataFrame(rows)
    output_path = RAW_DIR / "phishshift_raw.csv"
    data.to_csv(output_path, index=False)
    write_manifest(rows)
    print(f"Generated {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
