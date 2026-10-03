import json, datetime
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
records = [
    {"asset": "nostr:d83011abb7105211", "channel": "nostr", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "data/nostr_service_post.json: Lead Lists post 1/2 relays", "timestamp": now, "verification_status": "verified"},
    {"asset": "gpsr-landing lead form", "channel": "customer_site", "classification": "OBSERVED", "evidence_type": "bugfix", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "gpsr-landing now posts to real /api/customer/interest (was dead /api/customer/lead)", "timestamp": now, "verification_status": "verified"},
]
with open("data/commercial_evidence.jsonl", "a", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")
cyc = {"cycle_id": "S3-EXEC-05-CONT-03", "at": now, "publications": ["nostr:d83011abb7105211 (Lead Lists)"], "fixes": ["gpsr-landing lead loop"], "sales": 0, "revenue": 0, "cost_usd": 0, "founder_interventions": 0, "next": "monitor window to 2026-10-05"}
with open("data/production_cycles.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(cyc) + "\n")
print("logged")
