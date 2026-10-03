import json, datetime
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
records = [
    {"asset": "nostr:db53f03486f9ecc7", "channel": "nostr", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "Restaurant kit post 2/2 relays", "timestamp": now, "verification_status": "verified"},
    {"asset": "nostr:2d037734d0604e49", "channel": "nostr", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "STR kit post 2/2 relays", "timestamp": now, "verification_status": "verified"},
    {"asset": "nostr:123cd3e50853dab3", "channel": "nostr", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "ADA kit post 2/2 relays", "timestamp": now, "verification_status": "verified"},
    {"asset": "nostr:488c3d3225246092", "channel": "nostr", "classification": "OBSERVED", "evidence_type": "public_existence", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "Homebuyer kit post 2/2 relays", "timestamp": now, "verification_status": "verified"},
    {"asset": "freelancer:40747473", "channel": "freelancer", "classification": "OBSERVED", "evidence_type": "rejection", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "Bulk Excel-to-PDF, budget 750-1250 over policy max 250", "timestamp": now, "verification_status": "verified"},
    {"asset": "pending_review queue", "channel": "factory", "classification": "OBSERVED", "evidence_type": "queue_check", "funnel_stage": "E1", "human_or_automated": "automated", "raw_ref": "2 drafts correctly held (need human identity / X blocked); tier1 8 stale candidates untouched", "timestamp": now, "verification_status": "verified"},
]
with open("data/commercial_evidence.jsonl", "a", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")
cyc = {"cycle_id": "S3-LONGM-01", "at": now, "publications": ["restaurant", "str", "ada", "homebuyer (all 2/2)"], "production": ["queue checked, drafts correctly held"], "demand": ["freelancer scan 20, 1 match rejected over-bounds"], "sales": 0, "revenue": 0, "cost_usd": 0, "founder_interventions": 0, "next": "continue loop: VendorQ/DV/Mindfulness + monitor"}
with open("data/production_cycles.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(cyc) + "\n")
print("logged")
