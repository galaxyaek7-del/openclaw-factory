import json, datetime
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
inv = {
    "investigation_id": "JEV-PUBLISH-PROTECTION-01",
    "at": now,
    "phase1_freeze": {"PUBLISH_ACTION": "BLOCKED", "record": "data/investigation_freeze.json"},
    "phase2_failures": {
        "count": 7, "channel": "x", "window": "2026-10-03 ~07:09-07:38 UTC",
        "endpoint": "X API via x_queue.py --once from factory_loop maybeSendQueuedXPost (every tick)",
        "http_status": 402, "error": "credits depleted (no billing)",
        "root_cause": "MISSING_CREDENTIAL/billing — single common cause, replayed by tick polling",
        "classification": "PLATFORM_RESTRICTION (billing), NOT auth/network/content",
        "confidence": "high",
        "evidence": "data/publish_protection_state.json x.consecutive_failures=7; data/x_post_queue.json all blocked-payment after; factory_loop tick code"
    },
    "phase4_lead": {
        "event": "08:35 local CUSTOMER INTEREST (product عام)",
        "ledger_match": "int_1747b5ac49fd428d received 07:35:14Z, email verify-loop@t.com, message TEST_EVENT",
        "classification": "TEST_ARTIFACT — investigator's own accept-cycle proof firing the new Telegram alert code",
        "commercial_status": "NOT_A_LEAD, NOT_A_SALE, revenue unaffected",
        "lead_commercial_status": "UNKNOWN (zero real signals in ledger)",
        "sale": "NOT_VERIFIED"
    },
    "phase7_retry": {
        "retry_loop": "NO — tick polling with protection cooldown (by design); all 3 queue posts now blocked-payment so executor skips; attempts self-terminated",
        "evidence_preserved": True
    },
    "phase8_recovery": "WAIT_FOR_EXTERNAL_RECOVERY (FA-XCREDITS standing); protection self-releases per cooldown; no code change required",
    "phase9_release": "NO manual change to risk_score/counters; self-release per rules",
    "phase10_truth": {"sales": 0, "revenue": 0, "real_leads": 0, "interest_08_35": "test artifact, removed from ledger"},
    "phase11_code": "NO_CODE_CHANGE_REQUIRED",
    "founder_action": "none new (FA-XCREDITS already standing for X billing)",
    "next": "monitor: confirm no further x attempts post-blocked-payment; interest Telegram path proven live"
}
open("data/jev_protection_investigation.json", "w").write(json.dumps(inv, indent=1, ensure_ascii=False))
print("investigation recorded")
