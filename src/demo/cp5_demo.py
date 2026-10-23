from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "reports" / "cp5_demo.json"


def main() -> None:
    demo_payload = {
        "scenario": "CP-5 demo",
        "message": "Urgent password reset required. Verify your account now using hxxp://secure[.]portal[.]review/login before 5 PM.",
        "expected_verdict": "PHISHING-LIKELY",
        "risk_band": "76 / 100",
        "decision_support": "Decision support only - not a guarantee of safety.",
        "notes": [
            "Urgency and account verification language were detected.",
            "Defanged URL and portal lure were preserved without opening any link.",
            "Analyst should escalate to a trusted channel for confirmation.",
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(demo_payload, indent=2), encoding="utf-8")
    print(json.dumps(demo_payload, indent=2))


if __name__ == "__main__":
    main()
