from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

URL_RE = re.compile(r"https?://[^\s\)\]>\"]+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}(?!\w)")
CREDENTIAL_RE = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|credential)[=:]?\s*[A-Za-z0-9!@#$%^&*()_+\-={}|:;,.<>?/\\\[\]]+")
ATTACHMENT_RE = re.compile(r"(?i)(attachment|invoice\s*pdf|docx|xlsx|zip|\.pdf|\.docx|\.xls|\.zip)")


def defang_url(url: str) -> str:
    if not url:
        return ""
    value = url.strip()
    value = re.sub(r"^https?://", lambda m: "hxxps://" if m.group(0).startswith("https") else "hxxp://", value)
    value = value.replace(".", "[.]")
    return value


def is_defanged_url(url: str) -> bool:
    if not url or " " in url:
        return False
    return bool(re.match(r"^hxxps?://[A-Za-z0-9.-]+(?:\[\.\][A-Za-z0-9.-]+)*(?:/[A-Za-z0-9._~:/?#[\]@!$&'()*+,;=%-]*)?$", url))


def sanitize_text(value: str) -> str:
    text = value or ""
    text = re.sub(r"\b(?:https?|ftp)://[^\s]+", lambda m: defang_url(m.group(0)), text)
    text = re.sub(EMAIL_RE, "[email_redacted]", text)
    text = re.sub(PHONE_RE, "[phone_redacted]", text)
    text = re.sub(CREDENTIAL_RE, "[credential_redacted]", text)
    text = re.sub(r"(?i)\battachment[s]?\b[:\s]*[A-Za-z0-9._-]+\b", "[attachment_redacted]", text)
    text = re.sub(r"(?i)\b(?:pdf|zip|docx|xlsx|csv)\b", "[file_redacted]", text)
    return text


def extract_url_features(url: str) -> dict:
    url = url or ""
    if not url:
        return {
            "url_count": 0,
            "has_shortener": False,
            "has_ip_host": False,
            "num_dots": 0,
            "has_at_symbol": False,
            "path_depth": 0,
            "tld_class": "none",
            "lookalike_score": 0.0,
            "defanged": True,
        }
    host = url.replace("hxxp://", "").replace("hxxps://", "").split("/")[0]
    location = url.split("//", 1)[-1] if "//" in url else url
    path = location.split("/", 1)[1] if "/" in location else ""
    short_tokens = ["bitly", "tinyurl", "goo.gl", "short", "link", "rebrand"]
    return {
        "url_count": 1,
        "has_shortener": any(token in host.lower() for token in short_tokens),
        "has_ip_host": bool(re.search(r"\d+\.\d+\.\d+\.\d+", host)),
        "num_dots": host.count("[.]"),
        "has_at_symbol": "@" in host,
        "path_depth": len([segment for segment in path.split("/") if segment]),
        "tld_class": "shortener" if any(token in host.lower() for token in short_tokens) else "unknown",
        "lookalike_score": 0.85 if any(token in host.lower() for token in ["secure", "verify", "update", "portal"]) else 0.15,
        "defanged": True,
    }


def sanitize_record(row: dict) -> dict:
    url_value = row.get("sanitized_url_features", "")
    url_text = url_value if isinstance(url_value, str) else ""
    cleaned = {**row}
    cleaned["subject_or_title"] = sanitize_text(str(cleaned.get("subject_or_title") or ""))
    cleaned["body_text"] = sanitize_text(str(cleaned.get("body_text") or ""))
    cleaned["channel"] = str(cleaned.get("channel") or "").strip().lower()
    cleaned["label"] = str(cleaned.get("label") or "").strip().lower()
    if "http://" in url_text or "https://" in url_text:
        cleaned["sanitized_url_features"] = json.dumps(extract_url_features(defang_url(url_text)), sort_keys=True)
    else:
        cleaned["sanitized_url_features"] = json.dumps(extract_url_features(url_text), sort_keys=True)
    return cleaned
