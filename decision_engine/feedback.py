"""
Decision Engine — feedback from real sales (ADR-050).

Reads real "sale" events from data/sales_ledger.jsonl (channels/ledger.py,
ADR-016/ADR-... — the same file scripts/poll_sales.py writes to from a
platform's real get_sales() call). As of 2026-07-16 this file has zero
real sale events (only publish_attempt smoke-test records) — no live
platform API key exists yet (BLOCKERS.md #2). This module is real, tested
code, ready for that day; it is not simulated or fabricated to look like
it is already learning from data that does not exist yet.

Matching a sale back to the decision that led to it is inherently
best-effort: book_generator.py's generated product title is Groq-written
from the niche, not the niche string itself, so no guaranteed exact key
exists. This module only ever records a match when the decision's niche
text is actually found inside the sold product's own title/description —
never guesses, and every sale is recorded either way (matched or
honestly "unmatched"), so nothing real is ever silently dropped.
"""

import hashlib
import re
from datetime import datetime, timezone

from channels import ledger as sales_ledger

from decision_engine import store
from decision_engine.types import Outcome


def _normalize(text):
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _make_outcome_id(raw_sale_event):
    # Deterministic from the sale's own real fields — the same real sale
    # processed twice produces the same outcome_id, so re-running
    # sync_outcomes() never double-records it (checked against already-
    # recorded IDs below, same dedup discipline as scripts/poll_sales.py).
    raw = raw_sale_event.get("raw") or {}
    key = f"{raw_sale_event.get('platform')}|{raw.get('id') or raw.get('sale_id') or raw_sale_event.get('timestamp')}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _find_matching_decision(raw_sale_event, publish_attempts, decisions_by_niche):
    """Best-effort, real-fields-only match: sale -> publish_attempt (by
    product_id) -> decision (by niche substring appearing in the sold
    product's own recorded title). Returns (decision_or_None, method_str)."""
    raw = raw_sale_event.get("raw") or {}
    sale_product_id = raw.get("product_id") or raw.get("product_permalink")
    if sale_product_id is None:
        return None, "sale_has_no_product_id"

    matching_attempts = [
        a for a in publish_attempts
        if a.get("ok") and a.get("product_id") == sale_product_id and a.get("platform") == raw_sale_event.get("platform")
    ]
    if not matching_attempts:
        return None, "no_publish_attempt_matched_product_id"

    product_text = _normalize(
        f"{matching_attempts[-1].get('product_title', '')}"
    )
    for niche_key, decision in decisions_by_niche.items():
        if niche_key and niche_key in product_text:
            return decision, "niche_substring_in_product_title"

    return None, "product_title_matched_no_known_decision_niche"


def sync_outcomes(sales_ledger_path=None, decisions_path=None, outcomes_path=None):
    """Reads every real sale since the last sync, matches what it honestly
    can, and appends an Outcome for every one — matched or not. Never
    re-records a sale already processed (dedup by deterministic
    outcome_id, same discipline as scripts/poll_sales.py's sale dedup)."""
    sales = list(sales_ledger.read_events(event_type="sale", ledger_path=sales_ledger_path))
    if not sales:
        return {"synced": 0, "matched": 0, "unmatched": 0, "reason": "لا مبيعات حقيقية بعد في data/sales_ledger.jsonl"}

    publish_attempts = list(sales_ledger.read_events(event_type="publish_attempt", ledger_path=sales_ledger_path))
    decisions_by_niche = {
        d["niche"].strip().lower(): d
        for d in store.latest_decision_per_niche(path=decisions_path).values()
        if d.get("niche")
    }
    already_recorded = {o.get("outcome_id") for o in store.read_outcomes(path=outcomes_path)}

    synced = matched = unmatched = 0
    for sale in sales:
        outcome_id = _make_outcome_id(sale)
        if outcome_id in already_recorded:
            continue

        decision, method = _find_matching_decision(sale, publish_attempts, decisions_by_niche)
        outcome = Outcome(
            outcome_id=outcome_id,
            decision_id=decision.get("decision_id") if decision else None,
            niche=decision.get("niche") if decision else None,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            matched=decision is not None,
            match_method=method,
            raw_sale_event=sale,
        )
        store.append_outcome(outcome, path=outcomes_path)
        synced += 1
        if decision is not None:
            matched += 1
        else:
            unmatched += 1

    return {"synced": synced, "matched": matched, "unmatched": unmatched, "total_real_sales": len(sales)}
