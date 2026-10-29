"""Trend-to-Product: research source registry and trend signals (2026-10-29).

Pinterest and every other platform are treated as sources of market signals,
never as a store of assets. This module records WHERE a claim came from, WHEN it
was read, HOW it was accessed and WHAT it may be used for, and refuses records
that would need a prohibited access method.

Nothing here fetches anything. A source is recorded only after a person or a
Claude Code session actually read it (same discipline as
multi_source_intelligence/manual_verification.py and market_evidence.py).

Storage: append-only JSONL under data/trend_to_product/ (one record per line,
never rewritten). Every path is a parameter so tests never touch live files.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(ROOT, "data", "trend_to_product")

# How much a claim from this kind of source can be trusted. Ordered strongest
# first; the weight is used only to rank evidence, never to invent a number.
SOURCE_TYPES = {
    "OWN_PLATFORM_RECORD": 1.0,         # our own Gumroad/registry/ledger data
    "OFFICIAL_PLATFORM_DATA": 0.9,      # e.g. Pinterest Trends index read by a person
    "OFFICIAL_PLATFORM_REPORT": 0.7,    # e.g. Pinterest Predicts report
    "PLATFORM_TERMS": 0.9,              # terms/policy text (rules, not demand)
    "MARKETPLACE_LISTING": 0.6,         # a live listing: price/format, not sales
    "THIRD_PARTY_ESTIMATE": 0.4,        # keyword trackers, seller-tool sites
    "SECONDARY_COVERAGE": 0.35,         # press summarising an official report
    "ANECDOTAL": 0.15,
    "UNVERIFIED_SOCIAL": 0.1,           # a viral video, a post with no data
}

ACCESS_METHODS = {
    "MANUAL_SESSION_VIEW",      # a person/session opened the page
    "WEB_SEARCH_INDEX",         # read through a search engine's index summary
    "PUBLIC_API_KEYLESS",       # documented public API that needs no account
    "OFFICIAL_API_AUTHORIZED",  # an API the founder has authorised and configured
    "FACTORY_INTERNAL",         # our own files
}
# Never accepted, whatever the platform.
FORBIDDEN_ACCESS = {"SCRAPE", "AUTOMATED_SCRAPE", "LOGIN_BYPASS", "PAYWALL_BYPASS",
                    "RATE_LIMIT_EVASION", "HEADLESS_BULK_COLLECTION"}

# What the factory may do with material from the source, weakest first.
PERMITTED_USES = ("SIGNAL_ONLY", "CITATION_ONLY", "LICENSED_ASSET_USE", "OWN_ASSET")

# Per-platform rules. api_configured is False for every platform: no Pinterest
# or Etsy API credential exists in this factory, so no code may assume one.
PLATFORM_POLICY = {
    "pinterest": {
        "allowed_access": {"MANUAL_SESSION_VIEW", "WEB_SEARCH_INDEX", "OFFICIAL_API_AUTHORIZED"},
        "max_use": "CITATION_ONLY",
        "api_configured": False,
        "rule": "Pinterest terms prohibit collecting content by automated means without express "
                "prior permission; pins are signals and inspiration only (cited with a link), "
                "never assets.",
    },
    "etsy": {
        "allowed_access": {"MANUAL_SESSION_VIEW", "WEB_SEARCH_INDEX", "OFFICIAL_API_AUTHORIZED"},
        "max_use": "CITATION_ONLY",
        "api_configured": False,
        "rule": "Listings are read for price and format observations only.",
    },
    "gumroad": {
        "allowed_access": {"MANUAL_SESSION_VIEW", "WEB_SEARCH_INDEX", "FACTORY_INTERNAL",
                           "OFFICIAL_API_AUTHORIZED"},
        "max_use": "CITATION_ONLY",
        "api_configured": False,   # third-party sellers' pages; our own account is FACTORY_INTERNAL
        "rule": "Other sellers' listings are citations only.",
    },
    "_default": {
        "allowed_access": ACCESS_METHODS,
        "max_use": "CITATION_ONLY",
        "api_configured": False,
        "rule": "Third-party material is citable, not reusable, without a recorded licence.",
    },
}

SIGNAL_TYPES = {
    "SEARCH_INTEREST",       # relative search interest (an index, not a count)
    "TREND_DIRECTION",       # rising / falling / flat, with a period
    "CUSTOMER_PROBLEM",      # a repeated problem people state
    "SEASONALITY",
    "COMPETING_FORMAT",      # what already exists (incl. free alternatives)
    "COMPETITION_DENSITY",   # how many listings / sellers
    "PRICE_OBSERVATION",     # observed list prices
    "PLATFORM_RULE",         # terms, licence, policy
    "OBSERVED_SALE",         # only from our own platform records
}
# Signals that may ever be read as demand. None of them is proof of a sale.
DEMAND_SIGNALS = {"SEARCH_INTEREST", "TREND_DIRECTION", "CUSTOMER_PROBLEM", "SEASONALITY"}


class RecordError(ValueError):
    """A record that would break provenance, access or rights rules."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _id(prefix, *parts):
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{h}"


def platform_of(url):
    host = (urlparse(url or "").hostname or "").lower()
    labels = host.split(".")
    for name in ("pinterest", "etsy", "gumroad"):
        if name in labels:
            return name
    if host.endswith("patternbyetsy.com"):
        return "etsy"
    return "_default"


def _path(name, base_dir):
    return os.path.join(base_dir or DEFAULT_DIR, name)


def read_jsonl(name, base_dir=None):
    p = _path(name, base_dir)
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def _append(name, rec, base_dir=None):
    p = _path(name, base_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _index(name, key, base_dir=None):
    return {r[key]: r for r in read_jsonl(name, base_dir) if key in r}


# --------------------------------------------------------------------------- sources

def record_source(url, accessed_on, keyword, topic, source_type, access_method,
                  permitted_use="SIGNAL_ONLY", title=None, notes=None, licence=None,
                  rate_limit_note=None, base_dir=None):
    """Register one research source. Idempotent: the same url/date/keyword returns
    the existing record. Raises RecordError for anything the rules forbid."""
    if not url or not re.match(r"^https?://", url):
        raise RecordError("source needs an http(s) URL")
    try:
        datetime.strptime(accessed_on or "", "%Y-%m-%d")
    except ValueError:
        raise RecordError("accessed_on must be YYYY-MM-DD (the day it was actually read)")
    if not (keyword or "").strip() or not (topic or "").strip():
        raise RecordError("keyword and topic are required")
    if source_type not in SOURCE_TYPES:
        raise RecordError(f"unknown source_type {source_type!r}")
    if access_method in FORBIDDEN_ACCESS:
        raise RecordError(f"access method {access_method} is prohibited")
    if access_method not in ACCESS_METHODS:
        raise RecordError(f"unknown access_method {access_method!r}")
    if permitted_use not in PERMITTED_USES:
        raise RecordError(f"unknown permitted_use {permitted_use!r}")
    platform = platform_of(url)
    policy = PLATFORM_POLICY[platform]
    if access_method not in policy["allowed_access"]:
        raise RecordError(f"{access_method} is not allowed for {platform}")
    if access_method == "OFFICIAL_API_AUTHORIZED" and not policy["api_configured"]:
        raise RecordError(f"no authorised {platform} API is configured; do not assume one")
    cap = PERMITTED_USES.index(policy["max_use"])
    if PERMITTED_USES.index(permitted_use) > cap:
        # Asset use above the platform cap needs a licence that grants it.
        if not (licence and licence.get("commercial_use") is True and licence.get("reference")):
            raise RecordError(f"{permitted_use} from {platform} needs a recorded licence granting "
                              "commercial use; attribution alone is not permission")
        if platform == "pinterest":
            raise RecordError("Pinterest content is never used as a product asset")
    if source_type == "OWN_PLATFORM_RECORD" and access_method != "FACTORY_INTERNAL":
        raise RecordError("OWN_PLATFORM_RECORD must come from factory-internal data")

    sid = _id("SRC", url, accessed_on, keyword.strip().lower())
    existing = _index("sources.jsonl", "source_id", base_dir)
    if sid in existing:
        return existing[sid]
    rec = {
        "source_id": sid, "url": url, "title": title, "accessed_on": accessed_on,
        "keyword": keyword.strip(), "topic": topic.strip(), "source_type": source_type,
        "evidence_weight": SOURCE_TYPES[source_type], "access_method": access_method,
        "platform": platform, "permitted_use": permitted_use,
        "platform_rule": policy["rule"], "licence": licence, "rate_limit_note": rate_limit_note,
        "notes": notes, "recorded_at": _now(),
    }
    _append("sources.jsonl", rec, base_dir)
    return rec


# --------------------------------------------------------------------------- signals

def record_signal(signal_type, topic, claim, source_ids, observed_on, value=None,
                  label="OBSERVED", base_dir=None):
    """Record one material claim. Every claim cites at least one registered source.

    `label` follows the factory's evidence vocabulary: OBSERVED (read as stated in
    the source), DERIVED (computed from observed values), INFERRED, ESTIMATED.
    """
    if signal_type not in SIGNAL_TYPES:
        raise RecordError(f"unknown signal_type {signal_type!r}")
    if label not in ("OBSERVED", "DERIVED", "INFERRED", "ESTIMATED"):
        raise RecordError(f"unknown label {label!r}")
    if not (claim or "").strip():
        raise RecordError("claim text is required")
    if not source_ids:
        raise RecordError("every claim needs at least one source")
    try:
        datetime.strptime(observed_on or "", "%Y-%m-%d")
    except ValueError:
        raise RecordError("observed_on must be YYYY-MM-DD")
    sources = _index("sources.jsonl", "source_id", base_dir)
    missing = [s for s in source_ids if s not in sources]
    if missing:
        raise RecordError(f"unregistered source(s): {missing}")
    cited = [sources[s] for s in source_ids]
    if signal_type == "OBSERVED_SALE" and not all(c["source_type"] == "OWN_PLATFORM_RECORD" for c in cited):
        raise RecordError("a sale is only evidenced by our own platform records")
    if signal_type == "PRICE_OBSERVATION":
        if not isinstance(value, dict) or not value.get("currency") or value.get("low") is None \
                or value.get("high") is None or value["low"] > value["high"]:
            raise RecordError("PRICE_OBSERVATION needs value {currency, low, high[, median]} with low <= high")

    rec = {
        "signal_id": _id("SIG", signal_type, topic, claim, ",".join(sorted(source_ids))),
        "signal_type": signal_type, "topic": topic, "claim": claim.strip(), "value": value,
        "label": label, "observed_on": observed_on, "source_ids": list(source_ids),
        "evidence_weight": max(c["evidence_weight"] for c in cited),
        "source_types": sorted({c["source_type"] for c in cited}),
        # Search/trend interest is never read as sales. Only our own sale records are.
        "counts_as_sales_evidence": signal_type == "OBSERVED_SALE",
        "recorded_at": _now(),
    }
    existing = _index("signals.jsonl", "signal_id", base_dir)
    if rec["signal_id"] in existing:
        return existing[rec["signal_id"]]
    _append("signals.jsonl", rec, base_dir)
    return rec


def signals_for(topic=None, signal_ids=None, base_dir=None):
    out = read_jsonl("signals.jsonl", base_dir)
    if signal_ids is not None:
        wanted = set(signal_ids)
        out = [s for s in out if s["signal_id"] in wanted]
    if topic is not None:
        out = [s for s in out if s["topic"] == topic]
    return out
