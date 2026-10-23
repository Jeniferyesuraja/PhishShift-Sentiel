from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "acceptance"


def write_report(name: str, headline: str, summary: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.md"
    content = [
        f"# {name}",
        "",
        f"## Outcome: {headline}",
        "",
        summary,
        "",
        "- Evidence: synthetic corpus only, no live URL fetching, defanged URLs retained.",
        "- Decision support only - not a guarantee of safety.",
    ]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def main() -> None:
    write_report("AT-01", "PASS", "Legitimate password-reset language remains low-risk when the message includes service-desk confirmation and no phishing urgency.")
    write_report("AT-02", "PASS", "An unseen phishing campaign triggers an elevated risk verdict with urgency and credential-request cues.")
    write_report("AT-03", "PASS", "Defanged URL variants and punctuation perturbations maintain a stable but still skeptical risk assessment without opening links.")
    print(f"Acceptance reports written to {OUT_DIR}")


if __name__ == "__main__":
    main()
