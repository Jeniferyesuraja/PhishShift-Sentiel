from __future__ import annotations

import re


def score_message(text: str, sender_domain_type: str = "unknown", url_summary: dict | None = None) -> tuple[float, list[str]]:
    lowered = text.lower()
    urgency_words = ["urgent", "immediate", "today", "final", "now", "expire", "due", "lockout", "verify"]
    credential_words = ["password", "login", "credential", "reset", "security code", "verify identity"]
    threat_words = ["suspended", "deactivate", "blocked", "legal", "payment", "inbox", "quota"]
    score = 0.0
    cues: list[str] = []
    for word in urgency_words:
        if word in lowered:
            score += 0.12
            cues.append(f"urgency cue: {word}")
    for word in credential_words:
        if word in lowered:
            score += 0.18
            cues.append(f"credential ask: {word}")
    for word in threat_words:
        if word in lowered:
            score += 0.10
            cues.append(f"threat cue: {word}")
    if sender_domain_type in {"lookalike", "shortener", "unknown"}:
        score += 0.22
        cues.append(f"sender domain type: {sender_domain_type}")
    if url_summary:
        if url_summary.get("has_shortener"):
            score += 0.25
            cues.append("shortened or suspicious URL")
        if url_summary.get("lookalike_score", 0.0) > 0.5:
            score += 0.15
            cues.append("lookalike URL feature")
    punctuation_count = len(re.findall(r"[!?,;:]{2,}", text))
    if punctuation_count:
        score += 0.08 * punctuation_count
        cues.append("dense punctuation")
    if lowered.count("click") + lowered.count("link") > 0:
        score += 0.1
        cues.append("link action cue")
    if "dear" not in lowered and len(text.split()) > 7:
        score += 0.05
        cues.append("generic greeting absent")
    score = min(score, 1.0)
    return round(score, 4), cues
