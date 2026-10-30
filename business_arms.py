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
                           "services/spreadsheet_normalization/runbook.md",
                           "services/feed_preflight/preflight.py"],
        "acceptance": ["a written offer", "a working delivery engine", "a customer engagement"],
        "commercial_path": ["services/spreadsheet_normalization/offer.md", "services/feed_preflight/README.md"],
        "gap": "two tested services (catalogue clean-up, feed preflight) with draft pages; inquiries can arrive by e-mail and be recorded, but no offer page is published and no engagement exists",
        "blocker": "no published offer page (needs founder approval) and no customer engagement",
    },
    "research_data_services": {
        "name": "Research and Data Services",
        "implementation": ["market_intelligence_core", "multi_source_intelligence",
                           "competitor_discovery.py", "reports/B12-010/GATE_CANDIDATES_2026-10-19.json",
                           "data_products/datacard.py", "data_products/uspto_trademark_fees.py",
                           "services/research/uspto_trademark_fees_brief_2026-10-29.md",
                           "data_products/eaa_penalty_register.py"],
        "acceptance": ["repeatable research output", "a written offer", "a paying engagement"],
        "commercial_path": ["services/research/uspto_trademark_fees_brief_2026-10-29.md",
                            "services/research/eaa_penalty_register_brief_2026-10-29.md"],
        "gap": "two validated sample datasets with briefs (USPTO fees; EAA penalties, nine countries tied to the statutes); a draft page exists; not published, no buyer",
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
        # 2026-10-29: the customer-safe n8n automation audit (read-only public API,
        # same verdict rules as the internal health check) with a tested demo.
        "implementation": ["services/automation_health/audit.py", "services/automation_health/README.md"],
        "context": ["ai_capability/", "orchestrator/"],
        "acceptance": ["a customer-facing AI operations offer", "a delivery workflow", "a paying engagement"],
        "commercial_path": ["services/automation_health/README.md"],
        "gap": "offer with observed comparable prices ($14-$600 fix jobs, a $25 forum audit), tested audit demonstration and a draft page with an e-mail call to action; not published, no inquiry, no engagement",
        "blocker": "no recorded public intake; no customer engagement",
    },
    "productized_ai_services": {
        "name": "Productized AI Services",
        # 2026-10-29: accessibility quick-check (automated rules + human summary,
        # no AI model), tested; synthetic demo and a run on our own pages.
        "implementation": ["services/accessibility_check/check.py", "services/accessibility_check/README.md"],
        "acceptance": ["a scoped service offer", "a delivery workflow", "a paying engagement"],
        "commercial_path": ["services/accessibility_check/README.md"],
        "gap": "scoped offer and tested demonstration exist; no published page, no inquiry, no engagement",
        "blocker": "no recorded public intake; no customer engagement",
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
    # can promote it. An arm with its own revenue record (affiliate: REAL, PAID
    # commissions in commission_ledger, B22) is judged on that record; the
    # others need the company-wide reconciled finance record.
    own = cfg.get("arm_revenue_evidence")
    if own is not None:
        verified = own.get("status") == "PASS" and (own.get("usd") or 0) > 0
    else:
        verified = revenue.get("status") == "PASS" and (revenue.get("gross_usd") or 0) > 0
    if verified and cfg.get("arm_revenue_attributable"):
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


def _click_evidence(ledger_path=None) -> Dict[str, Any]:
    """Recorded affiliate clicks by class (affiliate_commerce/click_classification.py)."""
    try:
        from affiliate_commerce import click_classification as cc
        s = cc.summarize(ledger_path=ledger_path)
    except Exception:  # pragma: no cover - the arm keeps its fixed text
        return {}
    return {"total": s["total_recorded"], "counts": s["counts"], "possible_human": s["possible_human"]}


def _commission_evidence(ledger_path=None) -> Dict[str, Any]:
    """REAL commissions from commission_ledger (B22). TEST/SIMULATION/PROVISIONAL
    rows are never counted (commission_ledger.real_commission_summary)."""
    try:
        import commission_ledger
        s = commission_ledger.real_commission_summary(ledger_path)
    except Exception:  # pragma: no cover
        return {}
    return {"real_records": s["real_commission_records"],
            "paid_usd": s["real_paid_commission_usd"],
            "confirmed_or_paid_usd": s["real_confirmed_or_paid_commission_usd"],
            "test_records": s["test_records"]}


def _affiliate_cfg(cfg: Dict[str, Any], clicks: Dict[str, Any],
                   commissions: Dict[str, Any] = None) -> Dict[str, Any]:
    """Affiliate Intelligence restated from its own ledgers: clicks by class (B24)
    and REAL commissions (B22). Only a REAL, PAID commission is revenue for this
    arm; a CONFIRMED one is reported but promotes nothing."""
    commissions = commissions or {}
    if not (clicks and clicks.get("total")) and not commissions:
        return cfg
    out = dict(cfg)
    notes = []
    if clicks and clicks.get("total"):
        parts = ", ".join("%d %s" % (n, k) for k, n in clicks["counts"].items() if n)
        notes.append("%d click(s) recorded (%s); %d could be from an outside person"
                     % (clicks["total"], parts, clicks["possible_human"]))
    if commissions:
        paid = commissions.get("paid_usd") or 0
        conf = commissions.get("confirmed_or_paid_usd") or 0
        notes.append("REAL commissions: %d record(s), $%.2f paid, $%.2f confirmed or paid "
                     "(TEST rows excluded: %d)" % (commissions.get("real_records", 0), paid, conf,
                                                   commissions.get("test_records", 0)))
        out["arm_revenue_evidence"] = {"status": "PASS", "usd": paid, "source": "commission_ledger (REAL, PAID)"}
        if paid > 0:
            out["arm_revenue_attributable"] = True
    out["gap"] = "; ".join(notes)
    out["blocker"] = "AMAZON_ASSOCIATE_TAG is unset and no real affiliate account exists; " + out["gap"]
    return out


def _studio_evidence(root: Path = None) -> Dict[str, Any]:
    """Children's studio state from its own records: episode renders whose
    verify.json says PASS (proof-of-concept and test renders excluded), and the
    manifest's finished-film flag."""
    root = root or ROOT
    renders = root / "kids_studio" / "renders"
    verified = []
    for p in sorted(renders.glob("ep*.verify.json")) if renders.is_dir() else []:
        stem = p.name[: -len(".verify.json")]
        if any(t in stem for t in ("poc", "test")):
            continue
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("verdict") == "PASS":
                verified.append(stem)
        except (OSError, ValueError):
            continue
    try:
        finished = bool(json.loads((root / "kids_studio" / "production_manifest.json")
                                   .read_text(encoding="utf-8")).get("finished_film_exists"))
    except (OSError, ValueError):
        finished = None
    return {"verified_episode_renders": verified, "finished_film_exists": finished}


def _studio_cfg(cfg: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Children's Media Studio, restated from its verify records instead of fixed text."""
    n = len(evidence.get("verified_episode_renders") or [])
    if not n:
        return cfg
    out = dict(cfg)
    film = "no finished film exists" if evidence.get("finished_film_exists") is not True else "a finished film exists"
    channel = ("an automatic YouTube upload pipeline is built and waits for the founder's YouTube credentials "
               "and a per-episode approval" if (ROOT / "kids_studio" / "publishing" / "youtube_publisher.py").exists()
               else "no distribution channel is wired")
    out["gap"] = ("%d episode animatic(s) verified (%s); %s; %s"
                  % (n, ", ".join(evidence["verified_episode_renders"]), film, channel))
    out["blocker"] = out["gap"]
    return out


def _telegraph_evidence(root: Path = None) -> Dict[str, Any]:
    """Latest Telegraph getViews reading (scripts/distribution_metrics_daily.py)."""
    p = (root or ROOT) / "data" / "distribution_metrics.jsonl"
    last = None
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec.get("views"), dict):
                last = rec
    except OSError:
        return {}
    if not last:
        return {}
    ok = {k: v for k, v in last["views"].items() if isinstance(v, int)}
    return {"articles": len(ok), "views": sum(ok.values()), "read_at": last.get("timestamp")}


def _content_cfg(cfg: Dict[str, Any], tele: Dict[str, Any]) -> Dict[str, Any]:
    """Content and Distribution, restated from the latest Telegraph reading. The
    view counter is the platform's own (includes bots and our own loads), so it
    is exposure, never a measured audience response."""
    if not tele.get("articles"):
        return cfg
    out = dict(cfg)
    out["gap"] = ("Telegraph works: %d articles, %d views by the platform's counter (includes bots and own loads; "
                  "read %s); the X arm is credit-blocked; clicks and site visits are not measured, so no audience "
                  "response is established" % (tele["articles"], tele["views"], str(tele.get("read_at"))[:16]))
    out["blocker"] = "no click or visit measurement (analytics receiver needs the founder's account); X arm credit-blocked"
    return out


def arm_status() -> Dict[str, Any]:
    revenue = _revenue_state()
    evidence = _registry_evidence()
    cfgs = dict(ARMS)
    cfgs["digital_products"] = _digital_products_cfg(ARMS["digital_products"], evidence)
    cfgs["childrens_media_studio"] = _studio_cfg(ARMS["childrens_media_studio"], _studio_evidence())
    cfgs["content_distribution"] = _content_cfg(ARMS["content_distribution"], _telegraph_evidence())
    cfgs["affiliate_intelligence"] = _affiliate_cfg(ARMS["affiliate_intelligence"], _click_evidence(),
                                                    _commission_evidence())
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
    import arm_portfolio
    state = arm_status()
    company = arm_portfolio.summary(state)
    doc = {"generated_at": now or datetime.now(timezone.utc).isoformat(),
           "generated_by": "business_arms.write_state",
           "arms": state["arms"], "counts": state["counts"], "revenue": state["revenue"],
           "portfolio": portfolio_view(state), "controls": control_status(),
           "arm_portfolio": company,
           "problems": validate_arm_states(state) + company["problems"]}
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
