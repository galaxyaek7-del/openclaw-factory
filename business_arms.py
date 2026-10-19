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
                           "native_workbook_qa.py", "channels/", "distributor.py"],
        "acceptance": [
            "at least one product is checkout-verified",
            "a recorded, evidence-based release state",
            "a native quality gate for the shipped format",
        ],
        "commercial_path": ["channels/", "src/publish/"],
        "external_dependency": "founder listing authorization and a live Gumroad write credential in this environment",
        "blocker": "no verified external sale; three products are checkout-verified and all show zero sales",
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
    }


def arm_status() -> Dict[str, Any]:
    revenue = _revenue_state()
    arms = {key: evaluate_arm(key, cfg, revenue) for key, cfg in ARMS.items()}
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
    state = arm_status()
    print(json.dumps(state, ensure_ascii=False, indent=1))
    problems = validate_arm_states(state)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
