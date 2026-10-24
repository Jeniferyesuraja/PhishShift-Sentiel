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
    "The account review is still open and your approval is pending. Please confirm the latest access note through the portal before the end of the day.",
    "We noticed a mismatch in the account record and the review queue needs your confirmation before the reminder expires.",
    "Your profile requires a final check. Please review the approval request in the portal and confirm the update so the account stays active.",
    "The payment review is pending, and one outstanding access notice remains in the review page for confirmation today.",
    "This reminder is part of the account verification workflow. Please complete the review step in the portal and confirm before the deadline.",
    "The latest security audit found a pending action on your account. Please follow the portal instruction and approve the request before close.",
]

LEGIT_TEMPLATES = [
    "Your account review is complete and there is no further action required. The latest access note is available in the portal for reference.",
    "We noticed a mismatch in the account record and resolved it during the normal review process. No additional confirmation is needed.",
    "Your profile was checked during the standard approval routine, and the current status is active with no follow-up required.",
    "The payment review for this period is complete and no action is required unless a payroll adjustment is requested by the team.",
    "This reminder is part of the standard account verification workflow. The review step has already been completed and no urgent action is needed.",
    "The latest security audit confirms that no action is required for your account. Please keep this notice for your records and contact support if needed.",
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
            if label == "phishing":
                sender_domain_type = random.choice(["lookalike", "unknown", "freemail", "corporate"])
                subject = random.choice([
                    "Review needed",
                    "Account notice",
                    "Authorization request",
                    "Access update",
                    "Billing follow-up",
                    "Policy change alert",
                ])
                body = random.choice(PHISHING_TEMPLATES)
                if idx % 4 == 0:
                    body = body + " We recommend confirming the request before the business deadline so access stays active."
                if idx % 6 == 0:
                    body = body.replace("review", "review and confirm")
                base_url = random.choice(PHISHING_URLS)
            else:
                sender_domain_type = random.choice(["corporate", "unknown", "freemail", "lookalike"])
                subject = random.choice([
                    "Password reset confirmation",
                    "Payroll slip available",
                    "Scheduled IT maintenance",
                    "Corporate security notice",
                    "Travel approval confirmed",
                    "Benefits enrollment reminder",
                ])
                body = random.choice(LEGIT_TEMPLATES)
                if group in {"password_reset", "payroll_slip"} and idx % 3 == 0:
                    body = body + " This communication is informational and no urgent action is required."
                if idx % 7 == 0:
                    body = body + " If you did not make this request, contact the service desk to review the status."
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
