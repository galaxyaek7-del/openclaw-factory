"""Galaxy Forge — Niche Safety Filter v1

Gates every niche BEFORE it reaches book_generator.py.

Reads a JSON object from stdin describing a candidate product
({niche, title, subtitle, description, type}) and writes a JSON
verdict to stdout: {allowed, score, risk_level, reasons[]}.

Never raises — any failure still produces a valid, safe-by-default
JSON verdict on stdout with exit code 0.
"""

import sys
import json
import re
import unicodedata

# Category -> (risk_level, severity, keywords)
BLOCKLISTS = {
    "brand_poison": {
        "risk_level": "blocked",
        "severity": 100,
        "keywords": [
            "نصاب", "احتيال", "خداع", "غش", "مريب",
            "scam", "fraud", "fake", "cheat",
        ],
    },
    "financial": {
        "risk_level": "high",
        "severity": 50,
        "keywords": [
            "استثمار", "تداول", "أسهم", "فوركس", "ثراء سريع",
            "get rich quick", "forex secrets", "day trading",
        ],
    },
    "medical": {
        "risk_level": "high",
        "severity": 50,
        "keywords": [
            "علاج", "دواء", "شفاء",
            "cure", "treatment", "miracle cure", "detox",
        ],
    },
    "trademark": {
        "risk_level": "blocked",
        "severity": 100,
        "keywords": [
            "disney", "marvel", "pokemon", "nintendo",
            "harry potter", "nike",
        ],
    },
    "adult": {
        "risk_level": "blocked",
        "severity": 100,
        "keywords": [
            "إباحي", "porn", "explicit",
        ],
    },
}

# Arabic diacritics (tashkeel U+064B-U+065F), superscript alef (U+0670),
# small high marks (U+06D6-U+06ED), and tatweel (U+0640) — stripped
# before matching so "نِصَّاب" and "نصاب" match the same keyword.
ARABIC_DIACRITICS_RE = re.compile(
    "[ـً-ٰٟۖ-ۭ]"
)


def normalize(text):
    if not text:
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = ARABIC_DIACRITICS_RE.sub("", text)
    return text.lower().strip()


def collect_text(payload):
    fields = ["niche", "title", "subtitle", "description", "type"]
    parts = []
    for field in fields:
        value = payload.get(field)
        if isinstance(value, str):
            parts.append(value)
    return normalize(" ".join(parts))


def evaluate(payload):
    text = collect_text(payload)

    matches = []
    max_severity = 0
    worst_risk = "low"

    for category, rule in BLOCKLISTS.items():
        for keyword in rule["keywords"]:
            if normalize(keyword) in text:
                matches.append({"category": category, "keyword": keyword})
                if rule["severity"] > max_severity:
                    max_severity = rule["severity"]
                    worst_risk = rule["risk_level"]
                elif rule["severity"] == max_severity:
                    if rule["risk_level"] == "blocked":
                        worst_risk = "blocked"

    allowed = worst_risk not in ("blocked", "high")
    score = max(0, 100 - max_severity)
    reasons = [f"{m['category']}:{m['keyword']}" for m in matches]

    return {
        "allowed": allowed,
        "score": score,
        "risk_level": worst_risk,
        "reasons": reasons,
    }


def safe_default(reason):
    return {
        "allowed": False,
        "score": 0,
        "risk_level": "error",
        "reasons": [f"compliance_filter_error:{reason}"],
    }


def emit(obj):
    # Force UTF-8 on stdout regardless of the platform's console codepage
    # (Windows defaults stdout to cp1252, which mangles Arabic text).
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    try:
        # Read raw bytes and decode as UTF-8 explicitly — sys.stdin.read()
        # would otherwise use the platform's default codepage (e.g. cp1252
        # on Windows) and corrupt Arabic input.
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw.strip() else {}
            if not isinstance(payload, dict):
                payload = {}
        except (json.JSONDecodeError, ValueError):
            emit(safe_default("invalid_json"))
            return

        result = evaluate(payload)
        emit(result)
    except Exception as exc:
        emit(safe_default(str(exc)))


if __name__ == "__main__":
    main()
