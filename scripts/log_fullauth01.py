import json, datetime
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
records = [
    {"asset": "nostr:8ff1c1148a16051f", "channel": "nostr", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "data/nostr_service_post.json: EPR kit post 2/2 relays", "timestamp": now, "verification_status": "verified"},
    {"asset": "customer inbound routes audit", "channel": "customer_site", "classification": "OBSERVED", "evidence_type": "audit", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "support-ticket pure-Node OK; consultation/request-product spawn+argv OK; only interest route was broken (fixed); sole remaining execFile has no input", "timestamp": now, "verification_status": "verified"},
    {"asset": "systeme affiliate path", "channel": "affiliate", "classification": "OBSERVED", "evidence_type": "status_check", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "link live+tracked, nothing new to activate; same exposure bottleneck", "timestamp": now, "verification_status": "verified"},
]
with open("data/commercial_evidence.jsonl", "a", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")
cyc = {"cycle_id": "S3-EXEC-05-FULLAUTH-01", "at": now, "publications": ["nostr:8ff1c1148a16051f (EPR)"], "fixes": ["interest route", "gpsr-landing loop"], "audits": ["all customer inbound routes", "execFile sweep", "systeme"], "sales": 0, "revenue": 0, "cost_usd": 0, "founder_interventions": 0, "next": "monitor window to 2026-10-05"}
with open("data/production_cycles.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(cyc) + "\n")
print("logged")
