#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge Contract Generator (Customer Platform Round 2, 2026-07-29).

Deterministic, template-only contract text for a real customer proposal --
zero LLM-generated narrative, same doctrine as the Business Dossier
(ADR-XXX, 2026-07-22 arc). Reuses trust/*.html's own honest-placeholder
convention ("Draft — ..." for anything not yet knowable, e.g. governing
law/jurisdiction) rather than inventing or guessing a legal term this
factory hasn't actually decided yet.

Fields are structured (not one prose blob) so the customer's own status
page can render each section distinctly, matching how the proposal box
already renders price/basis/evidence as separate fields rather than one
paragraph.
"""

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def generate_contract(request, proposal, catalog_match=None):
    """Real, deterministic contract for a specific priced proposal.

    request: the customer's intake record (name/company/description).
    proposal: record["proposal"] as already built by
        _run_qualification_and_pricing (price/currency/price_basis).
    catalog_match: record["catalog_match"] if this proposal matched a live
        catalog product, else None.
    """
    customer_name = (request.get("name") or "").strip()
    company = (request.get("company") or "").strip()
    customer_label = f"{customer_name} ({company})" if company else customer_name

    scope = (catalog_match or {}).get("title") or (request.get("description") or "").strip()

    return {
        "parties": {
            "provider": "Galaxy Forge",
            "customer": customer_label,
        },
        "scope": scope[:1000],
        "price": {
            "amount": proposal.get("price"),
            "currency": proposal.get("currency", "USD"),
            "basis": proposal.get("price_basis"),
        },
        "payment_terms": (
            "Payment is due in full via the secure checkout link before production begins. "
            "All prices are in USD unless otherwise stated on this page."
        ),
        "delivery_expectations": (
            "Delivery timing depends on the production type for this item and is not fixed in "
            "advance. You'll be notified via your Galaxy Forge status page at every real stage, "
            "from Production through Delivery -- never a guessed date."
        ),
        "ip_terms": (
            "Upon full payment, you receive a license to use the delivered product for your own "
            "personal or business use. Resale or redistribution rights are not included unless "
            "explicitly agreed to in writing."
        ),
        "governing_law": (
            "Draft -- our operating jurisdiction and governing law haven't been confirmed yet. "
            "This section will name the real governing law before this document is finalized for "
            "launch, never guessed in the meantime."
        ),
        "generated_at": _now(),
        "accepted": False,
        "accepted_name": None,
        "accepted_at": None,
    }
