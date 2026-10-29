"""Business-arm status registry (Permanent Operating Doctrine, section 5).

The doctrine names the intended company shape and forbids marking an arm READY
because code or plans exist. This module states each arm's status from evidence
it can actually check at call time:

  READY             every declared acceptance criterion is met and a commercial
                    path exists
  PARTIAL           implementation evidence exists, specific gaps remain
  PLANNED           no implementation evidence for the arm itself
  BLOCKED           implementation exists but a named dependency prevents the
                    arm from progressing
  REVENUE_VERIFIED  real external revenue is attributable to the arm

`REVENUE_VERIFIED` is never inferred from company-wide revenue: no per-arm
attribution exists in this factory, so it stays unreachable until an arm has its
own transaction evidence. That is a real structural gap, not an oversight.

This deliberately does not duplicate `launch_readiness.py` (an 8-dimension
architecture score per division) or `commercial_readiness.py` (how close the
company is to commercial operation). It answers the narrower doctrine question:
"what state is this business arm actually in, and what proves it?"
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent

STATUSES = ("READY", "PARTIAL", "PLANNED", "BLOCKED", "REVENUE_VERIFIED")

ARMS: Dict[str, Dict[str, Any]] = {
    "digital_products": {
        "name": "Digital Products",
        "implementation": ["books/batch12", "operational_history.py",
                           "native_workbook_qa.py", "channels/", "distributor.py",
                           "product_registry.py"],
        "acceptance": [
            "at least one product is checkout-verified",
            "a recorded, evidence-based release state",
            "a native quality gate for the shipped format",
        ],
        "commercial_path": ["channels/", "src/publish/"],
        # Static fallback only. arm_status() replaces these with figures read
        # from data/product_registry.json (live Gumroad catalog) when it exists:
        # the 2026-10-19 text below said "no live Gumroad write credential",
        # which stopped being true once 102 listings went live.
        "external_dependency": "founder listing authorization and a live Gumroad write credential in this environment",
        "blocker": "no verified external sale; three products are checkout-verified and all show zero sales",
        "evidence_source": "data/product_registry.json",
    },
    "micro_b2b": {
        "name": "Micro-B2B Services",
        "implementation": ["services/spreadsheet_normalization/engine.py",
                           "services/spreadsheet_normalization/offer.md",
                           "services/spreadsheet_normalization/runbook.md"],
        "acceptance": ["a written offer", "a working delivery engine", "a customer engagement"],
        "commercial_path": ["services/spreadsheet_normalization/offer.md"],
        "gap": "no customer engagement or intake channel exists",
        "blocker": "no customer engagement or intake channel exists",
    },
    "research_data_services": {
        "name": "Research and Data Services",
        "implementation": ["market_intelligence_core", "multi_source_intelligence",
                           "competitor_discovery.py", "reports/B12-010/GATE_CANDIDATES_2026-10-19.json"],
        "acceptance": ["repeatable research output", "a written offer", "a paying engagement"],
        "commercial_path": [],
        "gap": "research infrastructure exists but no customer-facing offer exists",
        "blocker": "research infrastructure exists but no customer-facing offer or engagement",
    },
    "affiliate_intelligence": {
        "name": "Affiliate Intelligence",
        "implementation": ["affiliate_commerce/", "business_development.py",
                           "data/council_recommendations.jsonl"],
        "acceptance": ["a real affiliate account", "real tracked clicks", "confirmed commissions"],
        "commercial_path": ["affiliate_commerce/networks.py"],
        "external_dependency": "a real Amazon Associates account; AMAZON_ASSOCIATE_TAG is unset and only the founder can create the account",
        "blocker": "AMAZON_ASSOCIATE_TAG is unset and no real affiliate account was created; zero real clicks exist",
    },
    "content_distribution": {
        "name": "Content and Distribution",
        "implementation": ["content_generation/", "affiliate_content/",
                           "customer_site/", "channels/x_arm.py"],
        "acceptance": ["a publishing channel that succeeds", "repeated distribution", "measured audience response"],
        "commercial_path": ["channels/"],
        "gap": "the X publishing arm is credit-blocked; no measured audience response exists yet",
        "blocker": "the X publishing arm failed its last real attempts with HTTP 402 credits depleted",
    },
    "ai_operations": {
        "name": "AI Operations",
        "implementation": [],
        "context": ["ai_capability/", "orchestrator/"],
        "acceptance": ["a customer-facing AI operations offer", "a delivery workflow", "a paying engagement"],
        "commercial_path": [],
        "gap": "internal AI orchestration exists, but no customer-facing AI-operations arm was found",
        "blocker": "internal AI orchestration exists, but no customer-facing AI-operations arm was found",
    },
    "productized_ai_services": {
        "name": "Productized AI Services",
        "implementation": [],
        "acceptance": ["a scoped service offer", "a delivery workflow", "a paying engagement"],
        "commercial_path": [],
        "gap": "no implementation evidence found anywhere in the repository",
        "blocker": "no implementation evidence found anywhere in the repository",
    },
    "childrens_media_studio": {
        "name": "Children's Media Studio",
        "implementation": ["kids_studio/production_manifest.json",
                           "kids_studio/qa_checklist.md",
                           "kids_studio/rights_ledger.json",
                           "kids_studio/episodes"],
        "acceptance": ["a finished episode", "a distribution channel", "audience evidence"],
        "commercial_path": [],
        "gap": "one animatic exists; no finished film exists and no distribution channel is wired",
        "blocker": "one animatic exists; no finished film exists and no distribution channel is wired",
    },
}


# The founder's ten-activity portfolio (GF-FACTORY-WIDE-RECONSTRUCTION-AND-BUILD-v1,
# 2026-10-29) mapped onto the eight canonical arms above. The canonical arms are
# not renumbered or merged: an activity either maps to an existing arm, shares
# one with another activity (named in `shares_with`), or has no arm of its own
# yet (`arm: None`) and is reported PLANNED from its own evidence paths.
PORTFOLIO_ACTIVITIES: Dict[str, Dict[str, Any]] = {
    "digital_products": {"name": "Digital Products", "arm": "digital_products"},
    "productized_ai_services": {"name": "Productized AI Services", "arm": "productized_ai_services"},
    "micro_b2b": {"name": "Micro-B2B Products and Solutions", "arm": "micro_b2b"},
    "raas": {
        "name": "RaaS / results-oriented recurring operational services",
        "arm": None,
        "nearest_arm": "micro_b2b",
        "implementation": [],
        "note": "no recurring, outcome-priced service exists; services/spreadsheet_normalization "
                "is a one-off delivery engine under micro_b2b, not a recurring service",
    },
    "research_as_a_service": {"name": "Research-as-a-Service", "arm": "research_data_services",
                              "shares_with": "data_products_analytics"},
    "ai_operations": {"name": "AI Operations", "arm": "ai_operations"},
    "affiliate_intelligence": {"name": "Affiliate Intelligence", "arm": "affiliate_intelligence"},
    "data_products_analytics": {"name": "Data Products and Analytics", "arm": "research_data_services",
                                "shares_with": "research_as_a_service",
                                "note": "no dataset is packaged for sale; the shared arm covers research infrastructure"},
    "content_media": {"name": "Content and Media Production (incl. children's studio)",
                      "arm": "childrens_media_studio", "also": ["content_distribution"]},
    "distribution_reach": {"name": "Distribution, Marketing, Partnerships and Commercial Reach",
                           "arm": "content_distribution"},
}

# Cross-cutting control capabilities. They are not business arms and carry no
# revenue status; they are listed so the dashboard can show which module is
# authoritative for each and whether it is present. Both are advisory/read-only
# by construction: nothing here can move money or act on a recommendation.
CONTROL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "predictive_intelligence": {
        "name": "Predictive Intelligence",
        "authoritative": ["profit_oracle.py", "decision_engine/", "goos.py"],
        "supporting": ["growth_stages.py", "capital_allocation_engine.py", "multi_source_intelligence/"],
        "rule": "recommends only; scores are ESTIMATED, a forecast is never stored as an actual; "
                "acceptance still goes through decision_engine and the founder gates",
    },
    "treasury_control": {
        "name": "Treasury Control",
        "authoritative": ["revenue_truth.py", "channels/ledger.py", "commercial_reconciliation.py"],
        "supporting": ["revenue_os.py", "asymmetric_wallet.py", "scripts/poll_sales.py"],
        "rule": "visibility and reconciliation only; no module here initiates a payment, payout or transfer",
    },
}


def _exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def _revenue_state() -> Dict[str, Any]:
    try:
        import revenue_truth
        return revenue_truth.read_revenue_state()
    except Exception as exc:  # pragma: no cover - defensive, not expected
        return {"status": "UNKNOWN", "gross_usd": None, "note": str(exc)}


def evaluate_arm(key: str, cfg: Dict[str, Any], revenue: Dict[str, Any]) -> Dict[str, Any]:
    implementation = cfg.get("implementation") or []
    present = [p for p in implementation if _exists(p)]
    missing = [p for p in implementation if not _exists(p)]
    commercial = [p for p in (cfg.get("commercial_path") or []) if _exists(p)]

    if not present:
        status = "PLANNED"
    elif cfg.get("external_dependency"):
        status = "BLOCKED"
    elif cfg.get("gap"):
        status = "PARTIAL"
    elif commercial:
        status = "READY"
    else:
        status = "PARTIAL"

    # A real external transaction attributed to this arm is the only thing that
    # can promote it. No such attribution exists today, so this branch is
    # unreachable by design until arm-level transaction evidence is added.
    if revenue.get("status") == "PASS" and (revenue.get("gross_usd") or 0) > 0 \
            and cfg.get("arm_revenue_attributable"):
        status = "REVENUE_VERIFIED"

    if status in ("PARTIAL", "BLOCKED", "READY", "REVENUE_VERIFIED") and not present:
        status = "PLANNED"

    return {
        "arm": key,
        "name": cfg["name"],
        "status": status,
        "acceptance_criteria": cfg.get("acceptance") or [],
        "implementation_present": present,
        "implementation_missing": missing,
        "commercial_path_present": commercial,
        "external_dependency": cfg.get("external_dependency"),
        "gap": cfg.get("gap"),
        "blocker": cfg.get("blocker"),
        "evidence_basis": "path existence at call time plus the real revenue record",
        "arm_revenue_attributable": bool(cfg.get("arm_revenue_attributable")),
    }


def _registry_evidence(path: Path = None) -> Dict[str, Any]:
    """Published listings and Gumroad-reported sales from the product registry.

    The registry is rebuilt daily from a read-only GET of the live Gumroad
    catalog (scripts/registry_daily.py), so this is OBSERVED platform state."""
    path = path or ROOT / "data" / "product_registry.json"
    try:
        reg = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    products = reg.get("products") or []
    live = [p for p in products if p.get("published")]
    has_value = any("sales_usd_cents" in p for p in live)
    return {
        "source": str(path),
        "generated_at": reg.get("generated_at"),
        "products": len(products),
        "published": len(live),
        "sales_count": sum(int(p.get("sales_count") or 0) for p in live),
        "sales_usd_cents": sum(int(p.get("sales_usd_cents") or 0) for p in live) if has_value else None,
    }


def _digital_products_cfg(cfg: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Digital Products, restated from the registry instead of fixed text."""
    if not evidence or not evidence.get("published"):
        return cfg
    out = dict(cfg)
    out.pop("external_dependency", None)  # listing works: the products are live
    stamp = "registry %s" % (evidence.get("generated_at") or "time unknown")
    if evidence.get("sales_count"):
        cents = evidence.get("sales_usd_cents")
        amount = "unknown amount" if cents is None else "$%.2f gross" % (cents / 100)
        out["gap"] = ("%d listings live; Gumroad reports %d sale(s), %s (%s); not yet reconciled "
                      "with the finance record" % (evidence["published"], evidence["sales_count"], amount, stamp))
        # A sale on a Gumroad listing is the arm's own transaction evidence.
        out["arm_revenue_attributable"] = True
    else:
        out["gap"] = "%d listings live on Gumroad; no sale recorded on any of them (%s)" % (
            evidence["published"], stamp)
    out["blocker"] = out["gap"]
    return out


def arm_status() -> Dict[str, Any]:
    revenue = _revenue_state()
    evidence = _registry_evidence()
    cfgs = dict(ARMS)
    cfgs["digital_products"] = _digital_products_cfg(ARMS["digital_products"], evidence)
    arms = {key: evaluate_arm(key, cfg, revenue) for key, cfg in cfgs.items()}
    arms["digital_products"]["registry_evidence"] = evidence or None
    counts: Dict[str, int] = {s: 0 for s in STATUSES}
    for arm in arms.values():
        counts[arm["status"]] = counts.get(arm["status"], 0) + 1
    return {
        "arms": arms,
        "counts": counts,
        "revenue": {
            "status": revenue.get("status"),
            "gross_usd": revenue.get("gross_usd"),
            "sales_count": revenue.get("sales_count"),
            "note": "company-wide only; no per-arm attribution exists, so REVENUE_VERIFIED is unreachable today",
        },
        "honesty_note": "READY is not claimed for any arm: every arm with implementation evidence has either a named gap or an external dependency. REVENUE_VERIFIED requires arm-level attribution, which does not exist.",
    }


def portfolio_view(state: Dict[str, Any] = None) -> Dict[str, Any]:
    """The ten activities, each with the canonical arm it rests on and that arm's status."""
    state = state or arm_status()
    arms = state["arms"]
    rows = []
    for key, act in PORTFOLIO_ACTIVITIES.items():
        arm_key = act.get("arm")
        if arm_key:
            arm = arms[arm_key]
            row = {"activity": key, "name": act["name"], "arm": arm_key, "status": arm["status"],
                   "gap": arm.get("gap"), "blocker": arm.get("blocker")}
        else:
            present = [p for p in act.get("implementation") or [] if _exists(p)]
            row = {"activity": key, "name": act["name"], "arm": None,
                   "status": "PARTIAL" if present else "PLANNED",
                   "nearest_arm": act.get("nearest_arm"), "gap": act.get("note"), "blocker": act.get("note")}
        for extra in ("shares_with", "also", "note"):
            if act.get(extra) and extra not in row:
                row[extra] = act[extra]
        rows.append(row)
    return {"activities": rows,
            "taxonomy_note": "ten portfolio activities mapped onto the eight canonical doctrine arms; "
                             "canonical arms are not renumbered (see docs/factory/ARM_TAXONOMY.md)"}


def control_status() -> Dict[str, Any]:
    out = {}
    for key, cap in CONTROL_CAPABILITIES.items():
        auth = {p: _exists(p) for p in cap["authoritative"]}
        out[key] = {"name": cap["name"], "authoritative_present": auth,
                    "status": "PRESENT" if all(auth.values()) else "INCOMPLETE",
                    "supporting_present": [p for p in cap["supporting"] if _exists(p)],
                    "rule": cap["rule"]}
    rev = _revenue_state()
    out["treasury_control"]["revenue_record"] = {
        k: rev.get(k) for k in ("status", "gross_usd", "sales_count", "checked_at", "note")}
    return out


def write_state(path: Path = None, now: str = None) -> Dict[str, Any]:
    """Persist arms + portfolio + controls for the CEO dashboard (file reads only)."""
    from datetime import datetime, timezone
    state = arm_status()
    doc = {"generated_at": now or datetime.now(timezone.utc).isoformat(),
           "generated_by": "business_arms.write_state",
           "arms": state["arms"], "counts": state["counts"], "revenue": state["revenue"],
           "portfolio": portfolio_view(state), "controls": control_status(),
           "problems": validate_arm_states(state)}
    path = Path(path) if path else ROOT / "data" / "business_arms_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    import os
    os.replace(tmp, path)
    return doc


def validate_arm_states(state: Dict[str, Any]) -> List[str]:
    problems = []
    for key, arm in (state.get("arms") or {}).items():
        if arm["status"] not in STATUSES:
            problems.append("%s: unknown status %s" % (key, arm["status"]))
        if arm["status"] in ("READY", "PARTIAL", "BLOCKED", "REVENUE_VERIFIED") and \
                not arm["implementation_present"]:
            problems.append("%s: claims %s with no implementation evidence" % (key, arm["status"]))
        if arm["status"] == "READY" and (arm.get("external_dependency") or arm.get("gap")):
            problems.append("%s: claims READY while a gap or dependency is named" % key)
        if arm["status"] == "READY" and not arm["commercial_path_present"]:
            problems.append("%s: claims READY with no commercial path" % key)
        if arm["status"] == "REVENUE_VERIFIED" and not arm.get("arm_revenue_attributable"):
            problems.append("%s: claims REVENUE_VERIFIED without arm-level attribution" % key)
    return problems


def main() -> int:
    import sys
    if "--write" in sys.argv:
        doc = write_state()
        print(json.dumps({"written": "data/business_arms_state.json", "counts": doc["counts"],
                          "problems": doc["problems"]}, ensure_ascii=False))
        return 1 if doc["problems"] else 0
    state = arm_status()
    print(json.dumps(state, ensure_ascii=False, indent=1))
    problems = validate_arm_states(state)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
