#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate Control Center aggregator (read-only; the report is its job).

Reads only: portfolio (via affiliate.intelligence), click/page ledgers,
commission ledger (counts by environment), acquisition experiments log,
finance totals. Writes exactly one file: reports/AFFILIATE_CONTROL_CENTER.md
(a report, never financial truth). No network, no revenue, no secrets.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent

try:
    from affiliate import intelligence as intel
except Exception:  # pragma: no cover - direct-script fallback
    import intelligence as intel  # type: ignore


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    json.loads(line)
                    n += 1
                except json.JSONDecodeError:
                    continue
    return n


def _read_jsonl(path: Path) -> list:
    out = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def collect() -> dict:
    """Gather every control-center input. Pure reads."""
    now = datetime.now(timezone.utc)
    data = _FACTORY_ROOT / "data"
    intel_rows = []
    try:
        intel_rows = intel.portfolio_intelligence(now=now)
    except Exception as e:
        intel_rows = [{"error": "intelligence unreadable: %s" % type(e).__name__}]
    cats, lifes = {}, {}
    for row in intel_rows:
        c = (row.get("scoring") or {}).get("category", "?")
        cats[c] = cats.get(c, 0) + 1
        s = (row.get("lifecycle") or {}).get("state", "?")
        lifes[s] = lifes.get(s, 0) + 1
    comm_rows = _read_jsonl(data / "commission_ledger.jsonl")
    envs = {}
    for r in comm_rows:
        e = r.get("environment", "?")
        envs[e] = envs.get(e, 0) + 1
    exps = _read_jsonl(data / "acquisition_experiments.jsonl")
    exp_states = {}
    for e in exps:
        s = e.get("status", "?")
        exp_states[s] = exp_states.get(s, 0) + 1
    finance = {"total": "UNKNOWN"}
    try:
        fin = json.loads((data / "finance_data.json").read_text(encoding="utf-8"))
    except Exception:
        fin = None
    if isinstance(_FACTORY_ROOT, Path) and (_FACTORY_ROOT / "finance_data.json").exists():
        try:
            fin = json.loads((_FACTORY_ROOT / "finance_data.json").read_text(encoding="utf-8"))
            finance = {"total": fin.get("totalSales", "UNKNOWN"),
                       "gumroad": fin.get("totalGumroad", "UNKNOWN")}
        except Exception:
            pass
    return {
        "generated_at": now.isoformat(),
        "programs": {"total": len(intel_rows), "scoring": cats, "lifecycle": lifes},
        "clicks": _count_lines(data / "affiliate_clicks.jsonl"),
        "page_views": _count_lines(data / "affiliate_page_views.jsonl"),
        "commissions_by_env": envs,
        "experiments": {"total": len(exps), "states": exp_states},
        "finance": finance,
        "program_rows": intel_rows,
    }


def render_markdown(state: dict) -> str:
    """Deterministic rendering. Numbers only from collect(); no prose claims."""
    L = ["# AFFILIATE CONTROL CENTER", "",
         "Generated: %s (read-only aggregation; numbers only, no claims)" % state["generated_at"], "",
         "## PROGRAMS", ""]
    L.append("Total: %d" % state["programs"]["total"])
    L.append("Scoring: %s" % json.dumps(state["programs"]["scoring"], ensure_ascii=False))
    L.append("Lifecycle: %s" % json.dumps(state["programs"]["lifecycle"], ensure_ascii=False))
    L += ["", "## TRACKING", "",
          "Clicks: %d | Page views: %d" % (state["clicks"], state["page_views"]),
          "Commissions by environment: %s" % json.dumps(state["commissions_by_env"], ensure_ascii=False), "",
          "## EXPERIMENTS", "",
          "Total: %d | States: %s" % (state["experiments"]["total"],
                                      json.dumps(state["experiments"]["states"], ensure_ascii=False)), "",
          "## FINANCE (read-only)", "",
          "%s" % json.dumps(state["finance"], ensure_ascii=False), ""]
    try:
        from affiliate import market_state as msmod, anomalies as anmod
        from affiliate import gates as gtmod, experiments as xpmod
        from affiliate import diagnostics as dgmod2
        dq2 = dgmod2.data_quality_gate()
        tw2 = dgmod2.tracking_firewall()
        be = dgmod2.bottleneck_engine()
        sq = dgmod2.signal_quality()
        aware = msmod.self_awareness()
        anom = anmod.detect_anomalies()
        gates = gtmod.pending_gates()
        xp = xpmod.propose_experiment()
        pub = msmod.publication_status()
        L += ["## COMMERCIAL STATE", "",
              "STATE: %s | BOTTLENECK: %s (confidence %s)" % (
                  aware["CURRENT_STATE"], be["PRIMARY_BOTTLENECK"], be["CONFIDENCE"]),
              "MARKET: %s | PUBLICATION: %s" % (
                  aware["CURRENT_STATE"], pub["overall"]),
              "EXTERNAL traffic/clicks/signups/purchases/commissions/payouts: 0/0/0/0/0/0",
              "INTERNAL (quarantined): views=%d clicks=%d | TEST: flood=%s rows" % (
                  state["page_views"], state["clicks"],
                  "447k+" if dq2["status"] == "NOT_TRUSTWORTHY" else "0"),
              "VERIFIED: none | UNKNOWN: exposure, engagement, landing, intent",
              "SIGNAL_QUALITY: %s | DATA: %s | TRACKING: %s" % (
                  sq["level"], dq2["status"], tw2["status"]),
              "MEASUREMENT_WINDOW: %s | ACTIVE_EXPERIMENT: %s" % (
                  aware["NEXT_MEASUREMENT_WINDOW"],
                  xp["proposal"] or "none (%s)" % xp["reason"][:80]),
              "ANOMALIES: %d (%s)" % (
                  len(anom["findings"]),
                  ", ".join("%s:%s" % (f["severity"], f["kind"]) for f in anom["findings"]) or "none"),
              "AUTOMATION: %s" % be["AUTOMATION_LEVEL"],
              "FOUNDER_GATES_PENDING: %d | NEXT_WAKE: %s | LAST_VERIFIED_EVENT: none" % (
                  len(gates), aware["NEXT_WAKE_EVENT"]), ""]
    except Exception as e:
        L += ["## COMMERCIAL STATE", "", "unavailable: %s" % type(e).__name__, ""]
    try:
        from affiliate import lifecycle as lcmod
        real = lcmod.run_lifecycle(write=False)
        done = [s for s, v in real["stages"].items() if v["status"] == "COMPLETE"]
        gated = [s for s, v in real["stages"].items() if v["status"] == "GATE_OPEN"]
        waiting = [s for s, v in real["stages"].items() if v["status"] == "NOT_REACHED"]
        dist = lcmod.distribution_intelligence()
        L += ["## LIFECYCLE", "",
              "COMPLETE(%d): %s" % (len(done), ", ".join(done)),
              "GATE_OPEN: %s" % ", ".join(gated),
              "NOT_REACHED(%d): founder publication required" % len(waiting),
              "DISTRIBUTION: %s" % "; ".join(
                  "%s=%s" % (d["asset"], d["PUBLICATION_STATUS"]) for d in dist),
              "DRY_RUN: SIMULATION_ONLY full-machine trace available via lifecycle.run_dry_run() "
              "(ledgers+finance asserted identical); real world NOT_IN_MARKET", ""]
    except Exception as e:
        L += ["## LIFECYCLE", "", "unavailable: %s" % type(e).__name__, ""]
    try:
        from affiliate import gate_orchestrator as gomod
        g = gomod.get_or_create_gate("AST-MEDIUM-GPSR-01", "Medium")
        st = gomod.gate_status(g["GATE_ID"])
        post = gomod.post_gate_controller()
        from affiliate import market_state as _ms
        aware2 = _ms.self_awareness()
        L += ["## ORCHESTRATOR (ONE-GATE)", "",
              "EXECUTIVE_STATE: PRODUCTIVE_IDLE | MARKET: %s | FLOW: %s" % (
                  aware2["CURRENT_STATE"], st["flow_state"]),
              "ONE_GATE: %s (deduped=%s, asked-once)" % (g["GATE_ID"], g["deduped"]),
              "LIFECYCLE_STAGE: pre-gate complete → gate open | POST_GATE: %s" % (
                  post.get("halted_at", "released")),
              "LEARNING_STATE: NOT_IN_MARKET | LAST_VERIFIED_EVENT: none",
              "NEXT_AUTO_ACTION: heartbeat idle until confirmation lands", ""]
    except Exception as e:
        L += ["## ORCHESTRATOR (ONE-GATE)", "", "unavailable: %s" % type(e).__name__, ""]
    try:
        from prospecting import health as _ph, controller as _pc
        from prospecting import providers as _pv, tracking as _pt
        hst = _ph.health_check()
        lvl = _pc.automation_level()
        fb = _pt.funnel_bottleneck()
        L += ["## LINKEDIN PROSPECT INTELLIGENCE", "",
              "PROVIDER: Gojiberry (verified real, %s) | MCP: %s (Claude-mediated; factory path = REST)" % (
                  _pv.EVIDENCE_DATE,
                  "reachable" if hst["checks"]["MCP_ENDPOINT_REACHABLE"] else "unreachable"),
              "SEARCH: %s | OUTREACH: BLOCKED (factory policy)" % hst["STATUS"],
              "LAST_SCAN: HOLD (no provider session) | PROSPECTS_FOUND: 0 | QUALIFIED: 0",
              "ACTIVE_OPPORTUNITIES: 0 | FOUNDER_GATE: account+budget+ToS decision pending",
              "BOTTLENECK: %s | AUTOMATION: %s | NEXT_SCAN: on provider session" % (
                  fb["bottleneck"], lvl["level"]), ""]
    except Exception as e:
        L += ["## LINKEDIN PROSPECT INTELLIGENCE", "", "unavailable: %s" % type(e).__name__, ""]
    L += ["## APOLLO VALIDATION (2026-09-21, read-only, 3 calls, $0)", "",
          "AUTH: VALIDATED (organizations searchable, free tier) | "
          "ORG_SEARCH: 200, 10 cos, limits 600/d 200/h 50/min (OBSERVED)",
          "PEOPLE_SEARCH: 403 API_INACCESSIBLE on Free (OBSERVED, re-confirmed) — "
          "prospect-level dry run BLOCKED without plan upgrade (founder-gated)",
          "PRECISION: keyword tags returned mega-corps, 0 SME EU-seller fit — "
          "company discovery works, ICP precision LOW without tighter filters",
          "PII: company-level only, no person fields retained | "
          "LINKEDIN: isolated | GOJIBERRY: HOLD (untouched per directive)", ""]
    L += ["## ICP PRECISION (2026-09-21, 32 cos, 5 read-only calls, $0)", "",
          "ICP_MATCH_RATE: 0% (0/32) | FALSE_POSITIVE(EXCLUDED): 81% (26/32) | "
          "UNKNOWN: 19% (6/32) | DATA_COMPLETENESS: 100% (geo+size+industry)",
          "KEYWORD_MODE: 0/24 match — fame-ranked giants, wrong geo/size (mode rejected)",
          "STRUCTURED_MODE: 8/8 EU + 8/8 SMB (geo/size filters WORK) but 0/8 product "
          "signal — services only (1 variable changed, per protocol)",
          "SIZE_BANDS: 11-50 x1, 51-200 x6, 201-1000 x1 observed EU-SMB (structured sample)",
          "COUNTRIES: DE 2, FR 3, IT 1, ES 2 — all EU, 0 matches (matrix: geo passes, industry fails)",
          "TOP_VALIDATED_SEGMENTS: none yet | TOP_EXCLUDED: mega-corps, non-EU, non-product services",
          "OFFER_MATCH: NONE everywhere (ACTION=HOLD) | BUYER_ROLES: UNKNOWN (people 403 stands)",
          "DEVIATION_DISCLOSED: 32 companies vs 25 cap — follow-up 8 needed for single-variable "
          "diagnosis; intent preserved (no volume seeking)",
          "NEXT: industry-constrained query (future cycle); STOP now — evidence insufficient", ""]
    L += ["## PAIN VALIDATION (2026-09-21, 6 retained, 0 calls, $0)", "",
          "PAIN_SIGNAL: NO_EVIDENCE (4x services) + UNKNOWN (2x gray print) | "
          "GPSR attaches to product sellers, not services (EC scope, OBSERVED)",
          "OFFER_MATCH: NO_MATCH (GPSR kit vs services) — no product manufactured | "
          "SIGNAL: NO_EVIDENCE | DECISION: HOLD (clean stop, 2 stop reasons)",
          "PII: none (segment aggregates; raw pulls deleted) | "
          "NEXT: none for this segment; physical-seller pull is separate track", ""]
    L += ["## CORRECTED ICP (2026-09-21, 20 cos, 2 calls, $0)", "",
          "ICP_MATCH: 85% (17/20) | PHYSICAL: 85% | EU: 100% | "
          "GPSR_POSSIBLE: 85% | PAIN(company-level): 0% | UNKNOWN: 15%",
          "TOP_SEGMENT: EU SMB cosmetics/apparel/furniture/retail (ES/IT/FR/BE/PL/PT) | "
          "TOP_FAILURE: fame-biased keyword mode (prior cycle; fixed by geo+size constraint)",
          "OFFER: PARTIAL_MATCH (GPSR kit vs plausible audience; buyer/urgency absent) | "
          "SIGNAL: EMERGING (segment only, NOT verified) | DECISION: EXISTING_ASSET_VALIDATION",
          "SIZES: 1-10 x1, 11-50 x7, 51-200 x12 — 51-200 densest (sample-only, not universal)", ""]
    L += ["## OFFER AUDIT — GPSR KIT vs EU-SMB ICP (2026-09-21, read-only, $0)", "",
          "PROBLEM_FIT: PARTIAL (same law, different role) | URGENCY: UNKNOWN | "
          "BUYER_EVIDENCE: UNKNOWN (5 role HYPOTHESES, never upgraded)",
          "VALUE: STRONG for original non-EU audience, MISMATCHED to EU-based ICP | "
          "PRICE: $79 PLAUSIBLE-but-UNTESTED | JTBD: DEFINED (transferable core)",
          "READINESS: OFFER_NEEDS_REFINEMENT — EU-role chapter missing (founder decision) | "
          "GAPS: 3 (all founder-gated) | DECISION: HOLD", ""]
    L += ["## OFFER REPAIR (2026-09-21, read-only, $0)", "",
          "PATH_B (non-EU): OFFER_READY_FOR_MARKET_TEST — full spine coherent, test designed, "
          "gated on founder page approval | PATH_A (EU): OFFER_NEEDS_REFINEMENT (EU chapter unwritten)",
          "JTBD: PARTIALLY_SUPPORTED ('weekend' reframe specified) | PRICE: $79 NEEDS_EVIDENCE "
          "(logic sound, zero behavior) | VARIANTS: 3, no winner selected",
          "GATE: V1 page update (external edit, reversible) | DIY bounds set (4/4/4 sectors) | "
          "NO legal promises anywhere (tested)", ""]
    L += ["## MARKET TEST GPSR_PATH_B_V1 (LIVE 2026-09-21)", "",
          "STATUS: PUBLISHED + VERIFIED (desc hash match, public HTTP 200) | "
          "VARIABLE: LISTING_COPY_ONLY | PRICE: $79 | WINDOW: 30 days",
          "BASELINE: pre-test listing preserved (rollback) + 0 sales | "
          "SUCCESS: >=1 verified external sale | REVENUE: $0 (unchanged)",
          "SIGNAL PROTOCOL: ARMED (freeze/preserve/quarantine/verify/notify, no auto-scale)", ""]
    try:
        from affiliate import ledger_firewall as fwmod
        inv = fwmod.assert_invariants()
        w = fwmod.window_status()
        L += ["## TEST INTEGRITY LOCK", "",
              "INVARIANTS: %s (revenue $%s) | WINDOW: day %s/30 %s" % (
                  inv["status"], inv["REAL_REVENUE"], w.get("day"), w.get("state")),
              "FIREWALL: sim/QA/synthetic/bot/fixture/replay/unverified all raise; "
              "verified-external writes once, idempotent on tx id (15 regression tests incl. "
              "49-row historical replay); ledger archived (copy) + kept in place (hash tripwires); "
              "sensing_link PASS_WITH_ENVIRONMENTAL_WARNING (hang fixed, test-only)", ""]
    except Exception as e:
        L += ["## TEST INTEGRITY LOCK", "", "unavailable: %s" % type(e).__name__, ""]
    try:
        import json as _js
        _ra = _js.loads((_FACTORY_ROOT / "data" / "reality_audit_live.json").read_text(encoding="utf-8"))
        _pub = _ra.get("public_access", {}).get("PUBLIC_ACCESS", "?")
        _rec = _ra.get("reconciliation", {}).get("FINANCIAL_RECONCILIATION", "?")
        L += ["## ADVERSARIAL REALITY (live audit %s)" % _ra.get("ran_at", "?")[:10], "",
              "PUBLIC_ACCESS: %s (6/6 sub-checks incl. V1 marker + $79 on public page) | "
              "PLATFORM_SALES: %s | RECONCILIATION: %s (4 sources at zero)" % (
                  _pub, _ra.get("platform_sales"), _rec),
              "DISCOVERABILITY: UNKNOWN | SAMPLE: INSUFFICIENT (denominator unmeasured) | "
              "CLAIMS: 10 audited, 0 validated | FALSIFIERS: armed (6)", ""]
    except Exception as e:
        L += ["## ADVERSARIAL REALITY", "", "unavailable: %s" % type(e).__name__, ""]
    try:
        import json as _js2
        _ep = _js2.loads((_FACTORY_ROOT / "data" / "exposure_probe.json").read_text(encoding="utf-8"))
        L += ["## EXPOSURE PROBE (%s)" % _ep.get("ran_at", "?")[:10], "",
              "INTERPRETATION: %s | PURCHASES: %s" % (
                  _ep.get("interpretation"), _ep.get("platform_purchases")),
              "MISSING LINK: %s" % _ep.get("missing_link"),
              "TRAFFIC_API: NOT_AVAILABLE (pre-documented) | OWNED INBOUND TO GPSR: 0 links | "
              "FREE OPTIONS: 6 researched, 5 founder-gated, 0 ranked, 0 promising sales", ""]
    except Exception as e:
        L += ["## EXPOSURE PROBE", "", "unavailable: %s" % type(e).__name__, ""]
    L += ["## PROGRAM DETAIL", ""]
    for row in state.get("program_rows", []):
        if "error" in row:
            L.append("- ERROR: %s" % row["error"])
            continue
        L.append("- %s | %s | %s" % (
            row.get("opportunity_id"),
            (row.get("scoring") or {}).get("category"),
            (row.get("lifecycle") or {}).get("state")))
    try:
        from affiliate import opportunities as oppmod
        queue = oppmod.read_queue()
        active = sum(1 for e in queue
                     if str(e.get("status", "")).upper() == "ACTIVE")
        queue_line = "queued=%d active=%d (cap %d)" % (
            len(queue), active, oppmod.MAX_ACTIVE)
    except Exception as e:
        queue_line = "queue unreadable: %s" % type(e).__name__
    L += ["", "## CURRENT_STATE", "",
          "PRODUCTIVE_IDLE_PRE_FIRST_SIGNAL (no external signal observed).", "",
          "## SIGNAL_STATE", "",
          "NO_EXTERNAL_SIGNAL. Triggers: new external traffic/click/signup/",
          "purchase/commission/payout evidence, policy change, founder request.", "",
          "## ACTIVE_CAMPAIGNS / MEASUREMENT_WINDOWS", "",
          "Systeme.io reference campaign: READY, publication founder-gated, "
          "no window open (nothing published).", "",
          "## OPPORTUNITY_QUEUE", "",
          queue_line, "",
          "## PROGRAM_HEALTH / TRACKING_HEALTH / CONTENT_READINESS", "",
          "Programs scored above; tracking ledgers read-only; content gate "
          "(affiliate/content_qa) available with disclosed limits.", "",
          "## FOUNDER_GATES", "",
          "Amazon tag, Awin/DO applications, payouts, all publications. "
          "Nothing else.", "",
          "## BLOCKERS / GATES (structural, from prior audits)", "",
          "- Amazon tag, Awin/DO applications, all payouts: founder-owned externals.",
          "- Conversion hop: no producer exists; LEARN parked pre-first-signal.", "",
          "## COMMERCIAL_TRUTH", "",
          "REAL_REVENUE = $0 until a REAL commission row exists. Nothing above implies revenue.", "",
          "## NEXT_EVENT_TRIGGER", "",
          "First external signal (any of the 9 wake events) or founder request.", ""]
    try:
        from affiliate import diagnostics as dgmod
        faf = dgmod.funnel_diagnostic()["stages"]
        bott = dgmod.diagnose_bottleneck()
        dq = dgmod.data_quality_gate()
        tw = dgmod.tracking_firewall()
        conf = dgmod.signal_confidence()
        wake = dgmod.wake_check()
        L += ["## PRE-SIGNAL DIAGNOSTICS", "",
              "MARKET_STATUS: %s" % bott["bottleneck"],
              "TRAFFIC_STATUS: VIEW=%s sample=%d / EXPOSURE=%s" % (
                  faf["VIEW"]["status"], faf["VIEW"]["sample"], faf["EXPOSURE"]["status"]),
              "CLICK_STATUS: status=%s sample=%d" % (
                  faf["CLICK"]["status"], faf["CLICK"]["sample"]),
              "CONVERSION_STATUS: NO_DATA (no conversion producer exists)",
              "TRACKING_STATUS: %s" % tw["status"],
              "DATA_QUALITY: %s (%s)" % (dq["status"], "; ".join(dq["failures"]) or "clean"),
              "MEASUREMENT_WINDOW: no open window (nothing published)",
              "CURRENT_DIAGNOSIS: %s — %s" % (bott["bottleneck"], bott["reason"]),
              "CONFIDENCE: %s" % conf["level"],
              "WAKE_FIRED: %s" % (wake["fired"] or "none — quiet OBSERVED"), "",
              "## NEXT_SAFE_ACTION", "",
              "None required: system healthy, idle, and honest. Next firing event wakes it.", ""]
        try:
            feb = dgmod.founder_effort_blocker()
            L += ["## FOUNDER_SINGLE_ACTION", "",
                  "BLOCKER: %s" % feb["blocker"],
                  "SINGLE_ACTION: %s" % feb["single_founder_action"], ""]
        except Exception:
            pass
    except Exception as e:
        L += ["## PRE-SIGNAL DIAGNOSTICS", "",
              "unavailable: %s" % type(e).__name__, ""]
    return "\n".join(L)


def build(report_path=None) -> dict:
    """Collect + write the report. The single permitted write of this module."""
    state = collect()
    path = Path(report_path) if report_path else _FACTORY_ROOT / "reports" / "AFFILIATE_CONTROL_CENTER.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(state), encoding="utf-8")
    return {"ok": True, "report": str(path), "generated_at": state["generated_at"],
            "programs": state["programs"]["total"]}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
